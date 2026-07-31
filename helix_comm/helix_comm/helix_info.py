"""Simple script to check Helix robot status via rosbridge."""

import sys

import rclpy
import roslibpy
from rclpy.node import Node

from helix_comm.config_loader import ConfigError, load_config


class HelixInfo(Node):
    """Check Helix robot status and available interfaces."""

    def __init__(self, host=None, port=None):
        super().__init__('helix_info')
        cfg = load_config()
        self.declare_parameter('host', cfg['host'])
        self.declare_parameter('port', cfg['port'])

        host = host if host is not None else self.get_parameter('host').value
        port = port if port is not None else self.get_parameter('port').value

        self.client = roslibpy.Ros(host=host, port=port)
        self.client.run()

        if not self.client.is_connected:
            self.get_logger().error(f'[FAILED] Cannot connect to {host}:{port}')
            sys.exit(1)

        self.get_logger().info(f'[OK] Connected to Helix robot at {host}:{port}')

    def print_info(self):
        """Print robot information."""
        self.get_logger().info('\n========== HELIX ROBOT INFO ==========')

        # Topics
        self.get_logger().info('\n-- Topics:')
        for t in self.client.get_topics():
            self.get_logger().info(f'  {t}')

        # Services
        self.get_logger().info('\n-- Services:')
        for s in self.client.get_services():
            self.get_logger().info(f'  {s}')

        self.get_logger().info('\n======================================')

    def destroy(self):
        self.client.terminate()
        super().destroy_node()


HELP_EPILOG = """
EXAMPLES
--------
  helix_info
      Print robot status, topics and services, then exit.
  helix_info --host 192.168.238.104 --port 9090
      Check a specific robot.

NOTES
-----
- One-shot diagnostic: prints the robot connection status plus every
  topic and service it exposes, then exits (no streaming).
- The same settings can be passed as ROS 2 parameters instead:
  helix_info --ros-args -p host:=192.168.238.104 -p port:=9090
"""


def main(args=None):
    rclpy.init(args=args)

    import argparse
    parser = argparse.ArgumentParser(
        prog='helix_info',
        description='Check Helix robot status: prints connection info plus '
                    'all available topics and services.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_EPILOG)
    parser.add_argument('--host', default=None,
                        help='Robot rosbridge host (default: from helix_config.yaml)')
    parser.add_argument('--port', type=int, default=None,
                        help='Robot rosbridge port (default: from helix_config.yaml)')

    argv = rclpy.utilities.remove_ros_args(args or sys.argv)
    parsed = parser.parse_args(argv[1:])

    try:
        node = HelixInfo(host=parsed.host, port=parsed.port)
    except ConfigError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)

    node.print_info()
    node.destroy()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
