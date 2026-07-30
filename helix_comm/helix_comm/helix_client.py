#!/usr/bin/env python3
"""ROS 2 node that connects to the Helix robot via rosbridge WebSocket."""

import sys
import rclpy
from rclpy.node import Node
import roslibpy


class HelixClient(Node):
    """ROS 2 node that communicates with a Helix robot via rosbridge."""

    def __init__(self):
        super().__init__('helix_client')
        self.declare_parameter('host', '192.168.238.104')
        self.declare_parameter('port', 9090)

        host = self.get_parameter('host').value
        port = self.get_parameter('port').value

        self.get_logger().info(f'Connecting to Helix robot at {host}:{port}...')
        self.client = roslibpy.Ros(host=host, port=port)
        self.client.on_ready(lambda: self.get_logger().info('✅ Connected to Helix robot'))
        self.client.on_error(lambda e: self.get_logger().error(f'Connection error: {e}'))
        self.client.run()

        if self.client.is_connected:
            self.get_logger().info('✅ Rosbridge connection established')
        else:
            self.get_logger().error('❌ Failed to connect to robot')
            sys.exit(1)

    def get_topics(self):
        """Return list of available ROS topics."""
        return self.client.get_topics()

    def get_services(self):
        """Return list of available ROS services."""
        return self.client.get_services()

    def call_service(self, service_name, service_type, args=None):
        """Call a ROS service on the robot."""
        service = roslibpy.Service(self.client, service_name, service_type)
        request = roslibpy.ServiceRequest(args or {})
        result = service.call(request)
        return result

    def destroy(self):
        self.client.terminate()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = HelixClient()

    try:
        node.get_logger().info('\n--- Available Topics ---')
        for topic in node.get_topics():
            node.get_logger().info(f'  {topic}')

        node.get_logger().info('\n--- Available Services ---')
        for svc in node.get_services():
            node.get_logger().info(f'  {svc}')

        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
