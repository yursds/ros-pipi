"""Bridge robot topics from rosbridge to native ROS 2 for tools like PlotJuggler."""

import sys

import rclpy
import roslibpy
from rclpy.node import Node

from helix_comm.config_loader import ConfigError, load_config

# -- Message builders -------------------------------------------------

_MSG_BUILDERS = {}


def _joint_state_msg(data):
    from builtin_interfaces.msg import Time
    from sensor_msgs.msg import JointState
    from std_msgs.msg import Header
    msg = JointState()
    msg.header = Header()
    msg.header.stamp = Time(
        sec=data["header"]["stamp"]["sec"],
        nanosec=data["header"]["stamp"]["nanosec"],
    )
    msg.header.frame_id = data["header"].get("frame_id", "")
    msg.name = data["name"]
    msg.position = data["position"]
    msg.velocity = data.get("velocity", [])
    msg.effort = data.get("effort", [])
    return msg


_MSG_BUILDERS["sensor_msgs/msg/JointState"] = _joint_state_msg


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

DEFAULT_TOPICS = [
    "sensor_msgs/msg/JointState:/joint_states",
]


class HelixBridge(Node):
    """Bridge topics from rosbridge to native ROS 2.

    Subscribes to robot topics via roslibpy and republishes them as
    native ROS 2 topics so tools like PlotJuggler can see them.
    """

    def __init__(self, host=None, port=None, topics=None):
        super().__init__("helix_bridge")
        cfg = load_config()
        self.declare_parameter("host", cfg["host"])
        self.declare_parameter("port", cfg["port"])
        self.declare_parameter("topics", DEFAULT_TOPICS)

        host = host if host is not None else self.get_parameter("host").value
        port = port if port is not None else self.get_parameter("port").value
        topics_raw = topics if topics is not None else self.get_parameter("topics").value

        self.get_logger().info(f"Connecting to {host}:{port}...")
        self._client = roslibpy.Ros(host=host, port=port)
        self._client.on_ready(lambda: self.get_logger().info("Connected to robot"))
        self._client.run()

        if not self._client.is_connected:
            self.get_logger().error("Connection failed")
            sys.exit(1)

        self._ros_subs = []  # roslibpy subs
        self._native_pubs = {}   # native pubs keyed by topic name

        for entry in topics_raw:
            parts = entry.split(":", 1)
            if len(parts) != 2:
                self.get_logger().warn(f"Skipping invalid topic spec: {entry}")
                continue
            ros_type, topic_name = parts
            self._bridge_topic(topic_name, ros_type)

        self.get_logger().info(f"Bridge ready - forwarding {len(self._ros_subs)} topics")

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
            except Exception as e:  # noqa: BLE001 - best-effort unsubscribe at shutdown
                self.get_logger().debug(f"Unsubscribe failed: {e}")
        self._client.terminate()
        super().destroy_node()


HELP_EPILOG = f"""
TOPIC SPEC FORMAT
-----------------
Each topic is specified as ROS_TYPE:TOPIC_NAME, for example:
  sensor_msgs/msg/JointState:/joint_states

EXAMPLES
--------
  helix_bridge
      Bridge the default topics (see DEFAULT TOPICS below).
  helix_bridge --host 192.168.238.104 --port 9090
      Bridge a specific robot.
  helix_bridge --topics sensor_msgs/msg/JointState:/joint_states \\
                        sensor_msgs/msg/JointState:/extra_joints
      Bridge custom topics (repeat the option or pass several).

DEFAULT TOPICS
-------------
  {", ".join(DEFAULT_TOPICS)}

NOTES
-----
- The bridge runs until Ctrl+C. Use PlotJuggler (ROS 2 Topic Streamer)
  to visualize the bridged topics.
- Unsupported message types are published as JSON strings on a
  std_msgs/String topic.
- The same settings can be passed as ROS 2 parameters instead:
  helix_bridge --ros-args -p topics:='["sensor_msgs/msg/JointState:/joint_states"]'
"""


def main(args=None):
    rclpy.init(args=args)

    import argparse
    parser = argparse.ArgumentParser(
        prog="helix_bridge",
        description="Bridge Helix robot topics from rosbridge to native "
                    "ROS 2 topics, so tools like PlotJuggler can see them.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_EPILOG)
    parser.add_argument("--host", default=None,
                        help="Robot rosbridge host (default: from helix_config.yaml)")
    parser.add_argument("--port", type=int, default=None,
                        help="Robot rosbridge port (default: from helix_config.yaml)")
    parser.add_argument("--topics", nargs="*", default=None,
                        help=f"Topic specs ROS_TYPE:TOPIC_NAME to bridge "
                             f"(default: {', '.join(DEFAULT_TOPICS)})")

    argv = rclpy.utilities.remove_ros_args(args or sys.argv)
    parsed = parser.parse_args(argv[1:])

    try:
        node = HelixBridge(host=parsed.host, port=parsed.port,
                           topics=parsed.topics)
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
