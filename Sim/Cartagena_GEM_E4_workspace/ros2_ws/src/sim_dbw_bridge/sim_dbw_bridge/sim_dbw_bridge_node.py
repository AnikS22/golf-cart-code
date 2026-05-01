"""sim_dbw_bridge_node — simulated drive-by-wire translation layer.

Mirrors the real Teensy firmware (Software/firmware/common/include/dbw_can_protocol.h)
in pure ROS 2: same state machine, same safety gates, same topic interface to
the autonomy stack. Output goes to /cmd_vel (Twist) which the ros_gz_bridge
forwards to Gazebo's AckermannSteering plugin.

When the real cart's gem_dbw_bridge (C++) replaces this node, autonomy code
above this layer does NOT change.

Topic interface (autonomy ↔ DBW):
    Subscribed:
        /dbw/cmd        ackermann_msgs/AckermannDriveStamped  (steering_angle, speed)
        /dbw/enable     std_msgs/Bool                          (software arm)
        /joy            sensor_msgs/Joy                        (manual / state-machine btns)
        /odom           nav_msgs/Odometry                      (for /vehicle/speed feedback)
    Published:
        /cmd_vel                geometry_msgs/Twist     (to Gazebo via bridge)
        /vehicle/master_state   std_msgs/UInt8          (DISENGAGED=0/ARMED=1/ACTIVE=2/FAULT=3)
        /vehicle/fault_flags    std_msgs/UInt8          (bitfield matching dbw_can_protocol.h)
        /vehicle/speed          std_msgs/Float32        (m/s, from odom)

Safety gates (dropping any single one transitions ACTIVE → DISENGAGED or FAULT):
    1. /dbw/enable must be True
    2. /dbw/cmd watchdog: command must arrive within WATCHDOG_TIMEOUT_S
    3. Joystick deadman / E-stop button not pressed
    4. Speed governor: target speed clipped to GOVERNED_SPEED_MPS

Joystick mapping (Logitech F710 / Xbox-style, ROS Joy node defaults):
    Buttons:
        A (idx 0): ARM            — DISENGAGED → ARMED
        Y (idx 3): ENGAGE         — ARMED → ACTIVE
        B (idx 1): DISENGAGE      — any state → DISENGAGED
        Back (idx 6): SOFT E-STOP — any state → FAULT
        Start (idx 7): CLEAR_FAULT — FAULT → DISENGAGED  (sim-only; real cart needs key cycle)
"""

from enum import IntEnum
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from std_msgs.msg import Bool, UInt8, Float32
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from nav_msgs.msg import Odometry
from ackermann_msgs.msg import AckermannDriveStamped


# ─── Mirrors of dbw_can_protocol.h ───
# Keep these aligned with Software/firmware/common/include/dbw_can_protocol.h.

class MasterState(IntEnum):
    DISENGAGED = 0
    ARMED = 1
    ACTIVE = 2
    FAULT = 3


class Fault(IntEnum):
    OVERCURRENT     = 1 << 0
    ENCODER_SENSOR  = 1 << 1
    PLAUSIBILITY    = 1 << 2
    WATCHDOG        = 1 << 3
    RANGE_LIMIT     = 1 << 4
    DRIVER_OVERRIDE = 1 << 5
    HW_ESTOP        = 1 << 6
    EPAS_FAULT      = 1 << 7


# ─── Cart parameters ───
# Mirrors of cart_parameters.xacro values. If you change them in the xacro,
# change them here too. (TODO: load from a shared YAML to enforce parity.)
GOVERNED_SPEED_MPS   = 2.235   # 5 mph Phase 1 cap
MAX_ROAD_WHEEL_RAD   = 28.0 * math.pi / 180.0  # 28°
WATCHDOG_TIMEOUT_S   = 0.100   # 100 ms — matches dbw_can_protocol.h WATCHDOG_TIMEOUT_MS
LOOP_HZ              = 50      # state machine + cmd publish

# Joystick button indices (Logitech F710 / Xbox in XInput mode)
BTN_ARM      = 0
BTN_DISENG   = 1
BTN_ENGAGE   = 3
BTN_ESTOP    = 6
BTN_CLEAR    = 7


class SimDBWBridge(Node):
    def __init__(self):
        super().__init__("sim_dbw_bridge")

        # State
        self.master_state = MasterState.DISENGAGED
        self.fault_flags  = 0
        self.enable       = False
        self.last_cmd     = AckermannDriveStamped()
        self.last_cmd_time = self.get_clock().now()
        self.have_cmd     = False
        self.current_speed_mps = 0.0
        self.last_buttons = []

        qos_reliable = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        qos_be       = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)

        # ─── Subscribers ───
        self.create_subscription(
            AckermannDriveStamped, "/dbw/cmd", self._on_cmd, qos_reliable)
        self.create_subscription(
            Bool, "/dbw/enable", self._on_enable, qos_reliable)
        self.create_subscription(
            Joy, "/joy", self._on_joy, qos_be)
        self.create_subscription(
            Odometry, "/odom", self._on_odom, qos_be)

        # ─── Publishers ───
        self.pub_cmd_vel = self.create_publisher(Twist, "/cmd_vel", 10)
        self.pub_state   = self.create_publisher(UInt8, "/vehicle/master_state", 10)
        self.pub_faults  = self.create_publisher(UInt8, "/vehicle/fault_flags", 10)
        self.pub_speed   = self.create_publisher(Float32, "/vehicle/speed", 10)

        # ─── Main loop ───
        self.create_timer(1.0 / LOOP_HZ, self._step)

        self.get_logger().info(
            f"sim_dbw_bridge up. State={self.master_state.name}. "
            f"Press joystick A to ARM, Y to ENGAGE."
        )

    # ─── Callbacks ───
    def _on_cmd(self, msg: AckermannDriveStamped):
        self.last_cmd = msg
        self.last_cmd_time = self.get_clock().now()
        self.have_cmd = True

    def _on_enable(self, msg: Bool):
        self.enable = bool(msg.data)
        if not self.enable and self.master_state == MasterState.ACTIVE:
            self._transition(MasterState.DISENGAGED, "/dbw/enable went False")

    def _on_odom(self, msg: Odometry):
        v = msg.twist.twist.linear
        self.current_speed_mps = math.sqrt(v.x * v.x + v.y * v.y)

    def _on_joy(self, msg: Joy):
        # Detect button press edges (0 → 1 transitions only)
        new_buttons = list(msg.buttons)
        prev = self.last_buttons or [0] * len(new_buttons)

        def pressed(idx):
            return (idx < len(new_buttons) and idx < len(prev)
                    and new_buttons[idx] == 1 and prev[idx] == 0)

        if pressed(BTN_ESTOP):
            self.fault_flags |= Fault.HW_ESTOP
            self._transition(MasterState.FAULT, "Joystick E-STOP pressed")
        elif pressed(BTN_DISENG):
            self._transition(MasterState.DISENGAGED, "Joystick DISENGAGE pressed")
        elif pressed(BTN_ARM):
            self._try_arm()
        elif pressed(BTN_ENGAGE):
            self._try_engage()
        elif pressed(BTN_CLEAR):
            self._try_clear_fault()

        self.last_buttons = new_buttons

    # ─── State transitions ───
    def _try_arm(self):
        if self.master_state != MasterState.DISENGAGED:
            self.get_logger().warn(
                f"ARM ignored: state is {self.master_state.name}, must be DISENGAGED")
            return
        # Preconditions for ARM (mirror of Pedals Teensy logic)
        if self.fault_flags != 0:
            self.get_logger().warn(
                f"ARM blocked: fault_flags=0x{self.fault_flags:02x} (clear with Start button)")
            return
        self._transition(MasterState.ARMED, "ARM button pressed, preconditions OK")

    def _try_engage(self):
        if self.master_state != MasterState.ARMED:
            self.get_logger().warn(
                f"ENGAGE ignored: state is {self.master_state.name}, must be ARMED")
            return
        if not self.enable:
            self.get_logger().warn("ENGAGE blocked: /dbw/enable is False")
            return
        self._transition(MasterState.ACTIVE, "ENGAGE button pressed, /dbw/enable=True")

    def _try_clear_fault(self):
        # In sim we allow clearing FAULT with a button. On the real cart this
        # requires a key cycle (sticky-FAULT semantics in dbw_can_protocol.h).
        if self.master_state != MasterState.FAULT:
            return
        self.fault_flags = 0
        self._transition(MasterState.DISENGAGED, "FAULT cleared (sim only)")

    def _transition(self, new_state: MasterState, reason: str):
        if new_state == self.master_state:
            return
        self.get_logger().info(
            f"State: {self.master_state.name} → {new_state.name} ({reason})")
        self.master_state = new_state

    # ─── Main loop step (50 Hz) ───
    def _step(self):
        # Watchdog: in ACTIVE, command must arrive at >= 10 Hz (max 100 ms gap)
        if self.master_state == MasterState.ACTIVE and self.have_cmd:
            now = self.get_clock().now()
            gap = (now - self.last_cmd_time).nanoseconds * 1e-9
            if gap > WATCHDOG_TIMEOUT_S:
                self.fault_flags |= Fault.WATCHDOG
                self._transition(
                    MasterState.FAULT,
                    f"Watchdog: no /dbw/cmd for {gap*1000:.0f} ms")

        # Compute output
        cmd_vel = Twist()
        if self.master_state == MasterState.ACTIVE and self.enable and self.have_cmd:
            target_speed_mps = float(self.last_cmd.drive.speed)
            target_steer_rad = float(self.last_cmd.drive.steering_angle)

            # Speed governor (defense in depth — also enforced upstream in firmware)
            if abs(target_speed_mps) > GOVERNED_SPEED_MPS:
                target_speed_mps = math.copysign(GOVERNED_SPEED_MPS, target_speed_mps)
                self.fault_flags |= Fault.RANGE_LIMIT  # log the clip but don't fault out

            # Steering range check
            if abs(target_steer_rad) > MAX_ROAD_WHEEL_RAD:
                target_steer_rad = math.copysign(MAX_ROAD_WHEEL_RAD, target_steer_rad)

            # Pack into Twist for AckermannSteering plugin:
            #   linear.x  = forward speed (m/s)
            #   angular.z = steering angle (rad). Note: the Gazebo plugin treats
            #               this as front-wheel steering angle when wheel_base
            #               and kingpin_width are set in the URDF plugin block.
            cmd_vel.linear.x = target_speed_mps
            cmd_vel.angular.z = target_steer_rad
        else:
            # All non-ACTIVE states publish zero (DISENGAGED/ARMED/FAULT)
            cmd_vel.linear.x = 0.0
            cmd_vel.angular.z = 0.0

        self.pub_cmd_vel.publish(cmd_vel)

        # Publish telemetry (mirrors VEHICLE_STATE on real CAN bus)
        self.pub_state.publish(UInt8(data=int(self.master_state)))
        self.pub_faults.publish(UInt8(data=int(self.fault_flags)))
        self.pub_speed.publish(Float32(data=float(self.current_speed_mps)))


def main(args=None):
    rclpy.init(args=args)
    node = SimDBWBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
