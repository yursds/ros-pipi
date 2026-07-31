#!/usr/bin/env python3
"""ROS 2 node that connects to the Helix robot via rosbridge WebSocket."""

import sys
import rclpy
from rclpy.node import Node
import roslibpy

from helix_comm.config_loader import load_config, ConfigError


class HelixClient(Node):
    """ROS 2 node that communicates with a Helix robot via rosbridge."""

    def __init__(self, host=None, port=None):
        super().__init__('helix_client')
        cfg = load_config()
        self.declare_parameter('host', cfg['host'])
        self.declare_parameter('port', cfg['port'])

        host = host if host is not None else self.get_parameter('host').value
        port = port if port is not None else self.get_parameter('port').value

        self.get_logger().info(f'Connecting to Helix robot at {host}:{port}...')
        self.client = roslibpy.Ros(host=host, port=port)
        self.client.on_ready(lambda: self.get_logger().info('[OK] Connected to Helix robot'))
        self.client.on_error(lambda e: self.get_logger().error(f'Connection error: {e}'))
        self.client.run()

        if self.client.is_connected:
            self.get_logger().info('[OK] Rosbridge connection established')
        else:
            self.get_logger().error('[FAILED] Connection to robot failed')
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


HELP_EPILOG = """
EXAMPLES
--------
  helix_client
      Connect to the robot and list all its topics and services.
  helix_client --host 192.168.238.104 --port 9090
      Connect to a specific robot.

NOTES
-----
- The node stays connected (Ctrl+C to exit) and can be used as a
  building block for other tools that need the robot's interface list.
- The same settings can be passed as ROS 2 parameters instead:
  helix_client --ros-args -p host:=192.168.238.104 -p port:=9090
"""


def main(args=None):
    rclpy.init(args=args)

    import argparse
    parser = argparse.ArgumentParser(
        prog='helix_client',
        description='Low-level rosbridge client for the Helix robot: connects '
                    'and lists all available topics and services.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_EPILOG)
    parser.add_argument('--host', default=None,
                        help='Robot rosbridge host (default: from helix_config.yaml)')
    parser.add_argument('--port', type=int, default=None,
                        help='Robot rosbridge port (default: from helix_config.yaml)')

    argv = rclpy.utilities.remove_ros_args(args or sys.argv)
    parsed = parser.parse_args(argv[1:])

    try:
        node = HelixClient(host=parsed.host, port=parsed.port)
    except ConfigError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)

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
