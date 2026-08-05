"""Bridge robot topics from rosbridge to native ROS 2 for tools like PlotJuggler."""

import sys

import rclpy
import roslibpy
from rclpy.node import Node

from helix_comm.utils.config_loader import ConfigError, load_config

# -- Message builders -------------------------------------------------

_MSG_BUILDERS = {}


def _header(data):
    """Build a std_msgs/Header from a rosbridge header dict (may be empty)."""
    from builtin_interfaces.msg import Time
    from std_msgs.msg import Header

    header = Header()
    stamp = data.get("stamp") or {}
    header.stamp = Time(
        sec=stamp.get("sec", 0),
        nanosec=stamp.get("nanosec", 0),
    )
    header.frame_id = data.get("frame_id", "")
    return header


def _joint_state_msg(data):
    from sensor_msgs.msg import JointState

    msg = JointState()
    msg.header = _header(data.get("header") or {})
    msg.name = data["name"]
    msg.position = data["position"]
    msg.velocity = data.get("velocity", [])
    msg.effort = data.get("effort", [])
    return msg


_MSG_BUILDERS["sensor_msgs/msg/JointState"] = _joint_state_msg


def _float64_multi_array_msg(data):
    from std_msgs.msg import Float64MultiArray, MultiArrayDimension

    msg = Float64MultiArray()
    layout = data.get("layout") or {}
    for dim in layout.get("dim") or []:
        d = MultiArrayDimension()
        d.label = dim.get("label", "")
        d.size = dim.get("size", 0)
        d.stride = dim.get("stride", 0)
        msg.layout.dim.append(d)
    msg.layout.data_offset = layout.get("data_offset", 0)
    msg.data = data.get("data", [])
    return msg


_MSG_BUILDERS["std_msgs/msg/Float64MultiArray"] = _float64_multi_array_msg


def _float64_msg(data):
    from std_msgs.msg import Float64

    msg = Float64()
    msg.data = data.get("data", 0.0)
    return msg


_MSG_BUILDERS["std_msgs/msg/Float64"] = _float64_msg


def _pose_array_msg(data):
    from geometry_msgs.msg import Pose, PoseArray

    msg = PoseArray()
    msg.header = _header(data.get("header") or {})
    for pose in data.get("poses") or []:
        p = Pose()
        position = pose.get("position") or {}
        p.position.x = position.get("x", 0.0)
        p.position.y = position.get("y", 0.0)
        p.position.z = position.get("z", 0.0)
        orientation = pose.get("orientation") or {}
        p.orientation.x = orientation.get("x", 0.0)
        p.orientation.y = orientation.get("y", 0.0)
        p.orientation.z = orientation.get("z", 0.0)
        p.orientation.w = orientation.get("w", 1.0)
        msg.poses.append(p)
    return msg


_MSG_BUILDERS["geometry_msgs/msg/PoseArray"] = _pose_array_msg


def _twist_stamped_msg(data):
    from geometry_msgs.msg import Twist, TwistStamped, Vector3

    msg = TwistStamped()
    msg.header = _header(data.get("header") or {})
    linear = data.get("twist", {}).get("linear") or {}
    angular = data.get("twist", {}).get("angular") or {}
    msg.twist = Twist(
        linear=Vector3(
            x=linear.get("x", 0.0),
            y=linear.get("y", 0.0),
            z=linear.get("z", 0.0),
        ),
        angular=Vector3(
            x=angular.get("x", 0.0),
            y=angular.get("y", 0.0),
            z=angular.get("z", 0.0),
        ),
    )
    return msg


_MSG_BUILDERS["geometry_msgs/msg/TwistStamped"] = _twist_stamped_msg


def _generic_msg(data):
    """Fallback: publish the dict as a JSON string on a std_msgs/String."""
    import json

    from std_msgs.msg import String

    msg = String()
    msg.data = json.dumps(data)
    return msg


_MSG_BUILDERS["__generic"] = _generic_msg


def build_message(ros_type, data):
    builder = _MSG_BUILDERS.get(ros_type) or _MSG_BUILDERS["__generic"]
    return builder(data)


# -- Bridge configuration ---------------------------------------------

# Topics exposed by the Helix robot, per the official reference
# (eai-ag/ros-helix Topics_and_Services.md). Each entry is ROS_TYPE:TOPIC_NAME;
# the bridged topic keeps the same name so it matches the robot docs.
DEFAULT_TOPICS = [
    # ros2_control joint state broadcaster (plain name, common convention)
    "sensor_msgs/msg/JointState:/joint_states",
    # /tendon_transmission_node
    "sensor_msgs/msg/JointState:/tendon_transmission_node/tendon_states",
    "std_msgs/msg/Float64MultiArray:/tendon_transmission_node/commands",
    "std_msgs/msg/Float64MultiArray:/tendon_transmission_node/current_commands",
    # /helix_gripper_node
    "std_msgs/msg/Float64:/helix_gripper_node/command_increment",
    # /helix_cartesian_control_node
    "sensor_msgs/msg/JointState:/helix_cartesian_control_node/dxdyl_state",
    "geometry_msgs/msg/PoseArray:/helix_cartesian_control_node/cartesian_state",
    "std_msgs/msg/Float64MultiArray:/helix_cartesian_control_node/dxdyl_command",
    "geometry_msgs/msg/TwistStamped:/helix_cartesian_control_node/delta_increment",
    # ros2_control direct motor interface
    "std_msgs/msg/Float64MultiArray:/motor_head_joint_position_controller/commands",
    "std_msgs/msg/Float64MultiArray:/motor_head_joint_effort_controller/commands",
    "sensor_msgs/msg/JointState:/motor_head_joint_state_broadcaster/joint_states",
    "std_msgs/msg/Float64MultiArray:/gripper_joint_position_controller/commands",
    "sensor_msgs/msg/JointState:/gripper_joint_state_broadcaster/joint_states",
]

# std_srvs/Trigger services exposed by the robot, bridged as native ROS 2
# services. Services with custom types (helix_transmission_interfaces) are
# not bridged: the interface packages are proprietary and unavailable here,
# so call those via helix_control or roslibpy (see docs/).
DEFAULT_SERVICES = [
    "/tendon_transmission_node/switch_to_current_control",
    "/tendon_transmission_node/switch_to_position_control",
    "/tendon_transmission_node/set_motor_offsets",
    "/tendon_transmission_node/check_calibration",
    "/helix_cartesian_control_node/reset_model",
    "/helix_cartesian_control_node/activate_joystick_control",
    "/helix_cartesian_control_node/deactivate_joystick_control",
]


class HelixBridge(Node):
    """Bridge topics and services from rosbridge to native ROS 2.

    Subscribes to robot topics via roslibpy and republishes them as
    native ROS 2 topics so tools like PlotJuggler can see them. Also
    exposes the robot's std_srvs/Trigger services as native ROS 2
    services, forwarding each call over rosbridge.
    """

    def __init__(self, host=None, port=None, topics=None, services=None):
        super().__init__("helix_bridge")
        cfg = load_config()
        self.declare_parameter("host", cfg["host"])
        self.declare_parameter("port", cfg["port"])
        self.declare_parameter("topics", DEFAULT_TOPICS)
        self.declare_parameter("services", DEFAULT_SERVICES)

        host = host if host is not None else self.get_parameter("host").value
        port = port if port is not None else self.get_parameter("port").value
        topics_raw = (
            topics if topics is not None else self.get_parameter("topics").value
        )
        services_raw = (
            services if services is not None else self.get_parameter("services").value
        )

        self.get_logger().info(f"Connecting to {host}:{port}...")
        self._client = roslibpy.Ros(host=host, port=port)
        self._client.on_ready(lambda: self.get_logger().info("Connected to robot"))
        self._client.run()

        if not self._client.is_connected:
            self.get_logger().error("Connection failed")
            sys.exit(1)

        self._ros_subs = []  # roslibpy subs
        self._native_pubs = {}  # native pubs keyed by topic name
        self._native_srvs = []  # native service servers

        for entry in topics_raw:
            if not entry:
                continue
            parts = entry.split(":", 1)
            if len(parts) != 2:
                self.get_logger().warn(f"Skipping invalid topic spec: {entry}")
                continue
            ros_type, topic_name = parts
            self._bridge_topic(topic_name, ros_type)

        for service_name in services_raw:
            if not service_name:
                continue
            self._bridge_service(service_name)

        self.get_logger().info(
            f"Bridge ready - forwarding {len(self._ros_subs)} topics "
            f"and {len(self._native_srvs)} services"
        )

    def _bridge_topic(self, topic_name, ros_type):
        """Create a roslibpy subscriber + native publisher for one topic."""

        # Create native publisher
        from rclpy.qos import QoSProfile, ReliabilityPolicy

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        pub = self.create_publisher(self._resolve_type(ros_type), topic_name, qos)
        self._native_pubs[topic_name] = pub

        # Create roslibpy subscriber
        def callback(data, _topic=topic_name, _type=ros_type):
            try:
                msg = build_message(_type, data)
                self._native_pubs[_topic].publish(msg)
            except (KeyError, TypeError) as e:
                self.get_logger().warn(f"Failed to bridge {_topic}: {e}")

        sub = roslibpy.Topic(self._client, topic_name, ros_type)
        sub.subscribe(callback)
        self._ros_subs.append(sub)

        self.get_logger().info(f"  bridging {topic_name} ({ros_type})")

    def _bridge_service(self, service_name):
        """Expose a robot std_srvs/Trigger service as a native ROS 2 service.

        The native server forwards every call to the robot over rosbridge,
        so tools like `ros2 service call` work from inside the container.
        """
        from std_srvs.srv import Trigger

        def callback(request, response, _name=service_name):
            try:
                svc = roslibpy.Service(self._client, _name, "std_srvs/srv/Trigger")
                result = svc.call(roslibpy.ServiceRequest({}))
                response.success = bool(result.get("success", False))
                response.message = str(result.get("message", ""))
            except Exception as e:  # noqa: BLE001 - report to caller
                self.get_logger().error(f"Service {_name} failed: {e}")
                response.success = False
                response.message = f"bridge error: {e}"
            return response

        self.create_service(Trigger, service_name, callback)
        self._native_srvs.append(service_name)

        self.get_logger().info(
            f"  bridging service {service_name} (std_srvs/srv/Trigger)"
        )

    def _resolve_type(self, ros_type):
        """Resolve 'sensor_msgs/msg/JointState' to sensor_msgs.msg.JointState class."""
        parts = ros_type.split("/")
        pkg = parts[0]
        msg_name = parts[-1]
        mod = __import__(f"{pkg}.msg", fromlist=[msg_name])
        return getattr(mod, msg_name)

    def destroy(self):
        for sub in self._ros_subs:
            try:
                sub.unsubscribe()
            except Exception as e:  # noqa: BLE001 - best-effort shutdown
                self.get_logger().debug(f"Unsubscribe failed: {e}")
        self._client.terminate()
        super().destroy_node()


HELP_EPILOG = f"""
TOPIC SPEC FORMAT
-----------------
Each topic is specified as ROS_TYPE:TOPIC_NAME, for example:
  sensor_msgs/msg/JointState:/joint_states

SERVICE BRIDGING
----------------
Robot services of type std_srvs/srv/Trigger are exposed as native ROS 2
services with the same name, so they appear in `ros2 service list` and
can be called with `ros2 service call`. Services with proprietary types
(helix_transmission_interfaces) are NOT bridged: call those through
helix_control or roslibpy (see docs/topics_and_services.md).

EXAMPLES
--------
  helix_bridge
      Bridge the default topics and services (see DEFAULTS below).
  helix_bridge --host 192.168.238.104 --port 9090
      Bridge a specific robot.
  helix_bridge --topics sensor_msgs/msg/JointState:/joint_states \\
                        sensor_msgs/msg/JointState:/extra_joints
      Bridge custom topics (repeat the option or pass several).
  helix_bridge --services /tendon_transmission_node/check_calibration
      Bridge only the given Trigger services.
  helix_bridge --topics "" --services ""
      Bridge neither topics nor services (empty strings disable them).

DEFAULT TOPICS
--------------
  {", ".join(DEFAULT_TOPICS)}

DEFAULT SERVICES
----------------
  {", ".join(DEFAULT_SERVICES)}

NOTES
-----
- The bridge runs until Ctrl+C. Use PlotJuggler (ROS 2 Topic Streamer)
  to visualize the bridged topics.
- Command topics only carry data while the robot is streaming commands
  (e.g. while helix_control is running); state topics publish
  continuously.
- Unsupported message types are published as JSON strings on a
  std_msgs/String topic.
- The same settings can be passed as ROS 2 parameters instead:
  helix_bridge --ros-args -p topics:='["sensor_msgs/msg/JointState:/joint_states"]'
                 -p services:='["/tendon_transmission_node/check_calibration"]'
"""


def main(args=None):
    rclpy.init(args=args)

    import argparse

    parser = argparse.ArgumentParser(
        prog="helix_bridge",
        description="Bridge Helix robot topics from rosbridge to native "
        "ROS 2 topics, so tools like PlotJuggler can see them.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_EPILOG,
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Robot rosbridge host (default: from helix_config.yaml)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Robot rosbridge port (default: from helix_config.yaml)",
    )
    parser.add_argument(
        "--topics",
        nargs="*",
        default=None,
        help=f"Topic specs ROS_TYPE:TOPIC_NAME to bridge "
        f"(default: {len(DEFAULT_TOPICS)} topics, see epilog)",
    )
    parser.add_argument(
        "--services",
        nargs="*",
        default=None,
        help="std_srvs/Trigger service names to bridge as "
        "native ROS 2 services "
        f"(default: {len(DEFAULT_SERVICES)} services)",
    )

    argv = rclpy.utilities.remove_ros_args(args or sys.argv)
    parsed = parser.parse_args(argv[1:])

    try:
        node = HelixBridge(
            host=parsed.host,
            port=parsed.port,
            topics=parsed.topics,
            services=parsed.services,
        )
    except ConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
