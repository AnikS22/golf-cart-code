"""Pure Pursuit waypoint follower for the GEM E4 in Gazebo."""
import math

import rclpy
from geometry_msgs.msg import Point, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import ColorRGBA, Header
from visualization_msgs.msg import Marker, MarkerArray

# ---- tunables ----
LOOKAHEAD_DIST = 2.5       # meters; target point along the path this far from cart
SPEED = 1.5                # m/s forward speed
WHEELBASE = 2.565          # GEM E4 front-to-rear axle
GOAL_TOLERANCE = 0.5       # only used for non-looping end condition
LOOP_PATH = True

# Path geometry. Corner radius must exceed the cart's minimum turn radius
# (L / tan(max_steer) = 2.565 / tan(0.6458) ≈ 3.4 m) or the cart will drift outward.
PATH_SIDE = 10.0
PATH_RADIUS = 4.0
PATH_STEP = 0.5


def yaw_from_quat(qx: float, qy: float, qz: float, qw: float) -> float:
    siny = 2.0 * (qw * qz + qx * qy)
    cosy = 1.0 - 2.0 * (qy * qy + qz * qz)
    return math.atan2(siny, cosy)


def wrap_angle(a: float) -> float:
    return math.atan2(math.sin(a), math.cos(a))


def _rounded_square(side: float, radius: float, step: float):
    """Dense CCW waypoints along a rounded square whose outer corners are at
    (0,0), (side,0), (side,side), (0,side)."""
    W, R = side, radius
    segments = [
        ('leg', (R, 0.0),       (W - R, 0.0)),
        ('arc', (W - R, R),     3 * math.pi / 2, 2 * math.pi),
        ('leg', (W, R),         (W, W - R)),
        ('arc', (W - R, W - R), 0.0,             math.pi / 2),
        ('leg', (W - R, W),     (R, W)),
        ('arc', (R, W - R),     math.pi / 2,     math.pi),
        ('leg', (0.0, W - R),   (0.0, R)),
        ('arc', (R, R),         math.pi,         3 * math.pi / 2),
    ]
    pts = []
    for kind, *rest in segments:
        if kind == 'leg':
            (x0, y0), (x1, y1) = rest
            n = max(1, int(round(math.hypot(x1 - x0, y1 - y0) / step)))
            for k in range(n):
                t = k / n
                pts.append((x0 + t * (x1 - x0), y0 + t * (y1 - y0)))
        else:
            (cx, cy), a0, a1 = rest
            n = max(2, int(round(R * (a1 - a0) / step)))
            for k in range(n):
                a = a0 + (k / n) * (a1 - a0)
                pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    return pts


WAYPOINTS = _rounded_square(PATH_SIDE, PATH_RADIUS, PATH_STEP)


class PurePursuit(Node):
    def __init__(self):
        super().__init__('pure_pursuit')
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.marker_pub = self.create_publisher(MarkerArray, '/pure_pursuit/markers', 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.pose = None
        self.target_idx = 0
        self.create_timer(0.05, self.tick)
        self.create_timer(0.2, self.publish_markers)
        self.get_logger().info(
            f'pure_pursuit up: {len(WAYPOINTS)}-pt rounded square '
            f'(side={PATH_SIDE} m, r={PATH_RADIUS} m), v={SPEED} m/s, ld={LOOKAHEAD_DIST} m'
        )

    def on_odom(self, msg: Odometry):
        self.pose = msg.pose.pose

    def _closest_index(self, x: float, y: float) -> int:
        best_i, best_d = 0, float('inf')
        for i, (wx, wy) in enumerate(WAYPOINTS):
            d = (wx - x) * (wx - x) + (wy - y) * (wy - y)
            if d < best_d:
                best_i, best_d = i, d
        return best_i

    def _lookahead_index(self, closest: int, x: float, y: float) -> int:
        n = len(WAYPOINTS)
        for step in range(n):
            i = (closest + step) % n if LOOP_PATH else min(closest + step, n - 1)
            wx, wy = WAYPOINTS[i]
            if math.hypot(wx - x, wy - y) >= LOOKAHEAD_DIST:
                return i
            if not LOOP_PATH and i == n - 1:
                return i
        return closest

    def tick(self):
        if self.pose is None:
            return

        x = self.pose.position.x
        y = self.pose.position.y
        q = self.pose.orientation
        yaw = yaw_from_quat(q.x, q.y, q.z, q.w)

        closest = self._closest_index(x, y)
        self.target_idx = self._lookahead_index(closest, x, y)
        tx, ty = WAYPOINTS[self.target_idx]

        if not LOOP_PATH and closest == len(WAYPOINTS) - 1:
            if math.hypot(WAYPOINTS[-1][0] - x, WAYPOINTS[-1][1] - y) < GOAL_TOLERANCE:
                self.cmd_pub.publish(Twist())
                return

        dx = tx - x
        dy = ty - y
        alpha = wrap_angle(math.atan2(dy, dx) - yaw)
        ld = math.hypot(dx, dy)
        curvature = 2.0 * math.sin(alpha) / ld
        omega = SPEED * curvature

        cmd = Twist()
        cmd.linear.x = SPEED
        cmd.angular.z = omega
        self.cmd_pub.publish(cmd)

    def publish_markers(self):
        header = Header(frame_id='odom', stamp=self.get_clock().now().to_msg())
        arr = MarkerArray()

        path = Marker(header=header, ns='path', id=0, type=Marker.LINE_STRIP, action=Marker.ADD)
        path.scale.x = 0.15
        path.color = ColorRGBA(r=1.0, g=0.85, b=0.0, a=0.9)
        path.pose.orientation.w = 1.0
        loop_pts = list(WAYPOINTS) + ([WAYPOINTS[0]] if LOOP_PATH else [])
        path.points = [Point(x=float(px), y=float(py), z=0.1) for px, py in loop_pts]
        arr.markers.append(path)

        if 0 <= self.target_idx < len(WAYPOINTS):
            tx, ty = WAYPOINTS[self.target_idx]
            tgt = Marker(header=header, ns='lookahead', id=0, type=Marker.SPHERE, action=Marker.ADD)
            tgt.scale.x = tgt.scale.y = tgt.scale.z = 0.7
            tgt.color = ColorRGBA(r=0.2, g=1.0, b=0.2, a=0.95)
            tgt.pose.position = Point(x=float(tx), y=float(ty), z=0.5)
            tgt.pose.orientation.w = 1.0
            arr.markers.append(tgt)

        self.marker_pub.publish(arr)


def main():
    rclpy.init()
    node = PurePursuit()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd_pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
