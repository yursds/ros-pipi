#!/usr/bin/env python3
"""Simple script to check Helix robot status via rosbridge."""

import sys
import rclpy
from rclpy.node import Node
import roslibpy

from helix_comm.config_loader import load_config


class HelixInfo(Node):
    """Check Helix robot status and available interfaces."""

    def __init__(self):
        super().__init__('helix_info')
        cfg = load_config()
        self.declare_parameter('host', cfg['host'])
        self.declare_parameter('port', cfg['port'])

        host = self.get_parameter('host').value
        port = self.get_parameter('port').value

        self.client = roslibpy.Ros(host=host, port=port)
        self.client.run()

        if not self.client.is_connected:
            self.get_logger().error(f'❌ Cannot connect to {host}:{port}')
            sys.exit(1)

        self.get_logger().info(f'✅ Connected to Helix robot at {host}:{port}')

    def print_info(self):
        """Print robot information."""
        self.get_logger().info('\n========== HELIX ROBOT INFO ==========')

        # Topics
        self.get_logger().info('\n📡 Topics:')
        for t in self.client.get_topics():
            self.get_logger().info(f'  {t}')

        # Services
        self.get_logger().info('\n🔧 Services:')
        for s in self.client.get_services():
            self.get_logger().info(f'  {s}')

        self.get_logger().info('\n======================================')

    def destroy(self):
        self.client.terminate()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = HelixInfo()
    node.print_info()
    node.destroy()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
