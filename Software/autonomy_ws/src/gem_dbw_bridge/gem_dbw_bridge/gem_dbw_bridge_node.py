"""gem_dbw_bridge_node — real-cart drive-by-wire ROS↔CAN bridge.

Translates ROS 2 ackermann commands → CAN frames on can0 (DBW bus, 500 kbps,
matching dbw_can_protocol.h). Inverse direction: incoming *_STATUS,
ESTOP_STATE, VEHICLE_STATE frames → ROS topics.

This is a deliberately THIN bridge. The master state machine + safety
gating live on the Pedals Teensy (`Software/firmware/pedals_teensy/`).
The bridge:
  - Sends JETSON_HEARTBEAT (0x100) at 50 Hz UNCONDITIONALLY (so the
    Teensies don't watchdog-fault).
  - Sends STEER_CMD (0x110), THROTTLE_CMD (0x120), BRAKE_CMD (0x130)
    at 50 Hz when /dbw/cmd is fresh (≤100 ms old). Otherwise stops
    sending command frames (Teensies see the gap and zero outputs).
  - Republishes *_STATUS / VEHICLE_STATE frames as ROS topics.

The Teensies enforce the actual gates (master_state == ACTIVE, brake
pedal not pressed, E-stop loop closed, etc.) before doing anything with
the commands. We don't second-guess them on the ROS side.

Topic interface — IDENTICAL to sim_dbw_bridge so autonomy code is portable:
    Subscribed:
        /dbw/cmd        ackermann_msgs/AckermannDriveStamped
        /dbw/enable     std_msgs/Bool
    Published:
        /vehicle/master_state    std_msgs/UInt8       (DISENGAGED/ARMED/ACTIVE/FAULT)
        /vehicle/fault_flags     std_msgs/UInt8
        /vehicle/speed_mps       std_msgs/Float32
        /vehicle/gear            std_msgs/UInt8       (0=N, 1=F, 2=R, 3=Charging)
        /vehicle/voltage_v       std_msgs/Float32
        /vehicle/steering_rad    std_msgs/Float32     (measured handwheel→roadwheel)

Run:
    sudo ip link set can0 up type can bitrate 500000
    ros2 run gem_dbw_bridge gem_dbw_bridge_node
"""

import math
import struct
import threading
import time

import can
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from std_msgs.msg import Bool, UInt8, Float32
from ackermann_msgs.msg import AckermannDriveStamped


# ─── Mirrors of dbw_can_protocol.h ──────────────────────────────────────────
ID_JETSON_HEARTBEAT = 0x100
ID_STEER_CMD        = 0x110
ID_STEER_STATUS     = 0x111
ID_STEER_TORQUE_RAW = 0x112
ID_THROTTLE_CMD     = 0x120
ID_THROTTLE_STATUS  = 0x121
ID_BRAKE_CMD        = 0x130
ID_BRAKE_STATUS     = 0x131
ID_ESTOP_STATE      = 0x140
ID_MCU_HB_MOTION    = 0x150
ID_MCU_HB_PEDALS    = 0x151
ID_VEHICLE_STATE    = 0x160


# ─── Cart parameters (mirror cart_parameters.xacro) ─────────────────────────
GOVERNED_SPEED_MPS   = 2.235               # 5 mph
MAX_ROAD_WHEEL_RAD   = 28.0 * math.pi / 180.0
STEERING_RATIO       = 16.0
WATCHDOG_TIMEOUT_S   = 0.100               # cmd staleness threshold
LOOP_HZ              = 50
HEARTBEAT_HZ         = 50

# Throttle scaling: speed_mps → throttle_permil. Phase 1 uses a coarse linear
# map; Pedals Teensy enforces the hard speed cap at 250 permil regardless.
PHASE1_THROTTLE_PERMIL_AT_GOVERNED = 250   # 250/1000 ≈ 5 mph after Teensy cap


class GemDBWBridge(Node):
    def __init__(self, can_channel="can0"):
        super().__init__("gem_dbw_bridge")

        # ─── Open SocketCAN ───
        try:
            self.bus = can.interface.Bus(
                channel=can_channel, bustype="socketcan", bitrate=500000)
            self.get_logger().info(
                f"Opened CAN bus {can_channel} @ 500 kbps")
        except Exception as e:
            self.get_logger().error(
                f"Failed to open CAN: {e}. Did you run setup_can_bus.sh?")
            raise

        # ─── State ───
        self.last_cmd: AckermannDriveStamped | None = None
        self.last_cmd_time = self.get_clock().now()
        self.enable = True   # software /dbw/enable; default True so first-light
                             # is gated only by the dash hardware buttons
        self.hb_counter = 0
        self.shutdown_flag = threading.Event()

        # Cached telemetry from CAN (republished as ROS topics)
        self.cached = {
            "master_state":  0,
            "fault_flags":   0,
            "speed_mps":     0.0,
            "gear":          0,
            "voltage_v":     0.0,
            "steering_rad":  0.0,
        }

        qos_reliable = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)

        # ─── ROS Subscribers ───
        self.create_subscription(
            AckermannDriveStamped, "/dbw/cmd", self._on_cmd, qos_reliable)
        self.create_subscription(
            Bool, "/dbw/enable", self._on_enable, qos_reliable)

        # ─── ROS Publishers ───
        self.pub_master_state = self.create_publisher(UInt8, "/vehicle/master_state", 10)
        self.pub_fault_flags  = self.create_publisher(UInt8, "/vehicle/fault_flags", 10)
        self.pub_speed_mps    = self.create_publisher(Float32, "/vehicle/speed_mps", 10)
        self.pub_gear         = self.create_publisher(UInt8, "/vehicle/gear", 10)
        self.pub_voltage_v    = self.create_publisher(Float32, "/vehicle/voltage_v", 10)
        self.pub_steering_rad = self.create_publisher(Float32, "/vehicle/steering_rad", 10)

        # ─── 50 Hz TX timer ───
        self.create_timer(1.0 / LOOP_HZ, self._tx_tick)

        # ─── CAN RX thread ───
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self.rx_thread.start()

    # ─── ROS callbacks ──────────────────────────────────────────────────────
    def _on_cmd(self, msg: AckermannDriveStamped):
        self.last_cmd = msg
        self.last_cmd_time = self.get_clock().now()

    def _on_enable(self, msg: Bool):
        self.enable = bool(msg.data)

    # ─── 50 Hz TX loop ──────────────────────────────────────────────────────
    def _tx_tick(self):
        # 1. Heartbeat — UNCONDITIONAL. Teensies need to see this even in
        #    DISENGAGED state, otherwise their watchdog faults them out.
        self._tx_heartbeat()

        # 2. Command frames — only if /dbw/cmd is fresh AND software-enabled.
        if self.last_cmd is None:
            return
        gap_s = (self.get_clock().now() - self.last_cmd_time).nanoseconds * 1e-9
        if gap_s > WATCHDOG_TIMEOUT_S:
            return

        cmd = self.last_cmd.drive
        steer_rad_road  = float(cmd.steering_angle)
        speed_mps       = float(cmd.speed)

        # Range checks (defense in depth — Pedals Teensy clips again)
        if abs(steer_rad_road) > MAX_ROAD_WHEEL_RAD:
            steer_rad_road = math.copysign(MAX_ROAD_WHEEL_RAD, steer_rad_road)
        if abs(speed_mps) > GOVERNED_SPEED_MPS:
            speed_mps = math.copysign(GOVERNED_SPEED_MPS, speed_mps)

        # Convert: road-wheel rad → handwheel centi-degrees (CAN payload unit)
        wheel_rad = steer_rad_road * STEERING_RATIO
        wheel_centideg = int(round(wheel_rad * 18000.0 / math.pi))
        wheel_centideg = max(-32767, min(32767, wheel_centideg))

        # Convert: speed (m/s) → throttle permil (linear; Pedals Teensy
        # caps at 250 anyway, so this is just a Phase 1 placeholder).
        # Negative speed → set throttle to 0 + brake (brake is Phase 2)
        if speed_mps > 0:
            throttle_permil = int(speed_mps / GOVERNED_SPEED_MPS *
                                  PHASE1_THROTTLE_PERMIL_AT_GOVERNED)
            brake_permil = 0
        else:
            throttle_permil = 0
            # Phase 1: no software brake. Phase 2 will populate this from
            # speed_mps < 0 OR a separate brake_cmd topic.
            brake_permil = 0
        throttle_permil = max(0, min(1000, throttle_permil))
        brake_permil    = max(0, min(1000, brake_permil))

        enable_byte = 1 if self.enable else 0

        # Pack and send
        self._send(ID_STEER_CMD,
                   struct.pack("<hHB3s", wheel_centideg, 18000, enable_byte, b"\x00\x00\x00"))
        self._send(ID_THROTTLE_CMD,
                   struct.pack("<HB5s", throttle_permil, enable_byte, b"\x00\x00\x00\x00\x00"))
        self._send(ID_BRAKE_CMD,
                   struct.pack("<HB5s", brake_permil, enable_byte, b"\x00\x00\x00\x00\x00"))

    def _tx_heartbeat(self):
        self.hb_counter = (self.hb_counter + 1) & 0xFFFFFFFF
        # struct: <IBBH> = u32 counter + u8 state + u8 reserved + u16 crc
        # state byte mirrors what Pedals Teensy will report; we send 0 for now
        # since the bridge doesn't run its own state machine.
        payload = struct.pack("<IBBH", self.hb_counter, 0, 0, 0)
        self._send(ID_JETSON_HEARTBEAT, payload)

    def _send(self, can_id: int, data: bytes):
        msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=False)
        try:
            self.bus.send(msg, timeout=0.005)
        except can.CanError as e:
            self.get_logger().warning(f"CAN send failed (id=0x{can_id:03x}): {e}")

    # ─── CAN RX thread ──────────────────────────────────────────────────────
    def _rx_loop(self):
        while not self.shutdown_flag.is_set() and rclpy.ok():
            try:
                msg = self.bus.recv(timeout=0.5)
                if msg is None:
                    continue
                self._handle_rx(msg)
            except Exception as e:
                self.get_logger().warning(f"CAN rx error: {e}")
                time.sleep(0.1)

    def _handle_rx(self, msg: can.Message):
        if msg.is_extended_id:
            return  # we ignore extended IDs on DBW bus
        if len(msg.data) != 8:
            return
        d = bytes(msg.data)

        if msg.arbitration_id == ID_VEHICLE_STATE:
            speed_x100, gear, voltage_x10, link = struct.unpack("<HBHB", d[:6])
            speed_mph = speed_x100 / 100.0
            speed_mps = speed_mph * 0.44704
            self.cached["speed_mps"] = speed_mps
            self.cached["gear"]      = gear
            self.cached["voltage_v"] = voltage_x10 / 10.0
            self.pub_speed_mps.publish(Float32(data=float(speed_mps)))
            self.pub_gear.publish(UInt8(data=int(gear)))
            self.pub_voltage_v.publish(Float32(data=float(voltage_x10) / 10.0))

        elif msg.arbitration_id == ID_ESTOP_STATE:
            estop_loop, brake_pedal, wheel_torque, dash_switch, master_state = \
                struct.unpack("<BBBBB", d[:5])
            self.cached["master_state"] = master_state
            self.pub_master_state.publish(UInt8(data=int(master_state)))

        elif msg.arbitration_id == ID_STEER_STATUS:
            angle_centideg, motor_current_mA, fault_flags, epas_state, epas_err = \
                struct.unpack("<hhBBH", d)
            # centideg of handwheel → rad of road wheel
            steering_rad_road = (angle_centideg * math.pi / 18000.0) / STEERING_RATIO
            self.cached["steering_rad"] = steering_rad_road
            self.cached["fault_flags"]  = fault_flags
            self.pub_steering_rad.publish(Float32(data=float(steering_rad_road)))
            self.pub_fault_flags.publish(UInt8(data=int(fault_flags)))

        elif msg.arbitration_id in (ID_MCU_HB_MOTION, ID_MCU_HB_PEDALS):
            # Heartbeat — mostly we just look at the state byte to detect FAULT
            counter, state = struct.unpack("<IB", d[:5])
            if state == 3:  # MASTER_STATE_FAULT
                self.cached["master_state"] = state
                self.pub_master_state.publish(UInt8(data=int(state)))

        # ID_THROTTLE_STATUS, ID_BRAKE_STATUS, ID_STEER_TORQUE_RAW handled
        # similarly later — for now we don't republish them as ROS topics.

    # ─── Cleanup ────────────────────────────────────────────────────────────
    def destroy_node(self):
        self.shutdown_flag.set()
        try:
            self.bus.shutdown()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = GemDBWBridge()
    except Exception:
        rclpy.shutdown()
        raise
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
