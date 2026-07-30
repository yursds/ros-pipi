#!/usr/bin/env python3
"""Bridge robot topics from rosbridge to native ROS 2 for tools like PlotJuggler."""

import sys
import time
import rclpy
from rclpy.node import Node
import roslibpy

# ── Message builders ──────────────────────────────────────────────────

_MSG_BUILDERS = {}


def _joint_state_msg(data):
    from sensor_msgs.msg import JointState
    from builtin_interfaces.msg import Time
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


# ── Bridge configuration ─────────────────────────────────────────────

DEFAULT_TOPICS = [
    "sensor_msgs/msg/JointState:/joint_states",
]


class HelixBridge(Node):
    """Bridge topics from rosbridge → native ROS 2.

    Subscribes to robot topics via roslibpy and republishes them as
    native ROS 2 topics so tools like PlotJuggler can see them.
    """

    def __init__(self):
        super().__init__("helix_bridge")
        self.declare_parameter("host", "192.168.238.104")
        self.declare_parameter("port", 9090)
        self.declare_parameter("topics", DEFAULT_TOPICS)

        host = self.get_parameter("host").value
        port = self.get_parameter("port").value
        topics_raw = self.get_parameter("topics").value

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

        self.get_logger().info(f"Bridge ready — forwarding {len(self._ros_subs)} topics")

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
            except Exception as e:
                self.get_logger().warn(f"Failed to bridge {_topic}: {e}")

        sub = roslibpy.Topic(self._client, topic_name, ros_type)
        sub.subscribe(callback)
        self._ros_subs.append(sub)

        self.get_logger().info(f"  bridging {topic_name} ({ros_type})")

    def _resolve_type(self, ros_type):
        """Resolve 'sensor_msgs/msg/JointState' → sensor_msgs.msg.JointState class."""
        parts = ros_type.split("/")
        pkg = parts[0]
        msg_name = parts[-1]
        mod = __import__(f"{pkg}.msg", fromlist=[msg_name])
        return getattr(mod, msg_name)

    def destroy(self):
        for sub in self._ros_subs:
            try:
                sub.unsubscribe()
            except Exception:
                pass
        self._client.terminate()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = HelixBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
