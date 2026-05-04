"""joy_to_ackermann_node — Logitech F710 → /dbw/cmd (AckermannDriveStamped).

Published unconditionally at 50 Hz. When the deadman button is NOT held,
publishes zeros (so the cart coasts and the Pedals Teensy watchdog stays
content with fresh-but-zero commands).

F710 mapping (XInput mode, ROS joy_node defaults — Linux):
    Axes:
        0: left  stick X        →  steering (-1 left ... +1 right) [INVERTED]
        1: left  stick Y        →  unused
        2: LT  trigger          →  unused (resting +1, full -1; in F710 mode 'X' it's an axis)
        3: right stick X        →  unused
        4: right stick Y        →  unused
        5: RT  trigger          →  throttle (resting +1, full -1; remap to 0..1)
    Buttons:
        0: A      → ARM (sent to /dbw/buttons/arm)
        1: B      → DISENGAGE
        2: X      → unused
        3: Y      → ENGAGE
        4: LB     → reverse hold (while held, speed sign flips)
        5: RB     → DEADMAN — must hold for /dbw/cmd to be non-zero
        6: Back   → soft E-stop (sets /dbw/enable False)
        7: Start  → clear /dbw/enable (set True)

NOTE: The actual ARM / ENGAGE / DISENGAGE state transitions happen
on the Pedals Teensy via dash hardware buttons. This node optionally
*also* publishes button events as latched topics for HMI mirroring.
For first-light, the gamepad does NOT replace the dash buttons — you
arm/engage on the dash, then drive with the gamepad.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from std_msgs.msg import Bool
from sensor_msgs.msg import Joy
from ackermann_msgs.msg import AckermannDriveStamped


# ─── Tunable params (mirrors of cart_parameters.xacro) ──────────────────────
GOVERNED_SPEED_MPS    = 2.235     # 5 mph
MAX_ROAD_WHEEL_RAD    = 28.0 * math.pi / 180.0
LOOP_HZ               = 50

# F710 axis/button indices (XInput / Linux defaults)
AXIS_STEER       = 0    # left stick X (negative = right with default driver, we flip)
AXIS_THROTTLE_RT = 5    # right trigger (resting +1, full pull -1)
BTN_DEADMAN_RB   = 5    # right bumper
BTN_REVERSE_LB   = 4    # left bumper held = reverse
BTN_SOFT_ESTOP   = 6    # back
BTN_CLEAR        = 7    # start


def trigger_to_unit(axis_value: float) -> float:
    """F710 triggers rest at +1 and pull to -1; remap to 0..1."""
    return max(0.0, min(1.0, (1.0 - axis_value) * 0.5))


class JoyToAckermann(Node):
    def __init__(self):
        super().__init__("joy_to_ackermann")

        qos_be = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        qos_rel = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)

        self.create_subscription(Joy, "/joy", self._on_joy, qos_be)
        self.pub_cmd    = self.create_publisher(AckermannDriveStamped, "/dbw/cmd", qos_rel)
        self.pub_enable = self.create_publisher(Bool, "/dbw/enable", qos_rel)

        # Latest joystick state
        self.axes = []
        self.buttons = []

        # Software enable (Back = false, Start = true)
        self.software_enable = True

        self.create_timer(1.0 / LOOP_HZ, self._tick)
        self.get_logger().info(
            "joy_to_ackermann up. Hold RB (deadman) + push left stick / RT to drive.")

    def _on_joy(self, msg: Joy):
        prev_buttons = list(self.buttons)
        self.axes = list(msg.axes)
        self.buttons = list(msg.buttons)

        # Edge-detected button actions
        def edge(idx):
            return (idx < len(self.buttons) and idx < len(prev_buttons)
                    and self.buttons[idx] and not prev_buttons[idx])

        if edge(BTN_SOFT_ESTOP):
            self.software_enable = False
            self.pub_enable.publish(Bool(data=False))
            self.get_logger().warn("/dbw/enable = False (Back button — soft E-stop)")
        elif edge(BTN_CLEAR):
            self.software_enable = True
            self.pub_enable.publish(Bool(data=True))
            self.get_logger().info("/dbw/enable = True (Start button)")

    def _tick(self):
        cmd = AckermannDriveStamped()
        cmd.header.stamp = self.get_clock().now().to_msg()
        cmd.header.frame_id = "base_link"

        if (len(self.axes) <= max(AXIS_STEER, AXIS_THROTTLE_RT)
                or len(self.buttons) <= max(BTN_DEADMAN_RB, BTN_REVERSE_LB)):
            # Joy not yet received — publish zeros so Pedals Teensy stays awake
            self.pub_cmd.publish(cmd)
            return

        deadman = bool(self.buttons[BTN_DEADMAN_RB])
        reverse = bool(self.buttons[BTN_REVERSE_LB])

        if deadman and self.software_enable:
            # Steering: F710 left stick X. ROS convention positive = left, but
            # the F710 driver gives positive on right-push by default — flip.
            steer_norm = -self.axes[AXIS_STEER]
            steer_norm = max(-1.0, min(1.0, steer_norm))
            cmd.drive.steering_angle = steer_norm * MAX_ROAD_WHEEL_RAD

            # Throttle: RT 0..1 → speed
            throttle = trigger_to_unit(self.axes[AXIS_THROTTLE_RT])
            speed = throttle * GOVERNED_SPEED_MPS
            if reverse:
                speed = -speed
            cmd.drive.speed = float(speed)
        # else: zeros (default-constructed)

        self.pub_cmd.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = JoyToAckermann()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
