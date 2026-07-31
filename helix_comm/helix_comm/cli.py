"""CLI to control the Helix robot via rosbridge."""

import sys
import time

import rclpy
import roslibpy
from rclpy.node import Node

from helix_comm.actions import ACTIONS
from helix_comm.config_loader import ConfigError, load_config
from helix_comm.control.arm import Arm
from helix_comm.control.button import Button
from helix_comm.control.calibrate import Calibrate
from helix_comm.control.gripper import Gripper
from helix_comm.help_text import HELP_EPILOG


class HelixControl(Node):
    def __init__(self, host=None, port=None):
        super().__init__('helix_control')
        cfg = load_config()
        self.declare_parameter('host', cfg['host'])
        self.declare_parameter('port', cfg['port'])

        host = host if host is not None else self.get_parameter('host').value
        port = port if port is not None else self.get_parameter('port').value

        self.get_logger().info(f'Connecting to {host}:{port}...')
        self.client = roslibpy.Ros(host=host, port=port)
        self.client.on_ready(lambda: self.get_logger().info('Connected'))
        self.client.run()

        if not self.client.is_connected:
            self.get_logger().error('Connection failed')
            sys.exit(1)

        self.arm = Arm(self.client, self.get_logger())
        self.gripper = Gripper(self.client, self.get_logger())
        self.calibrate = Calibrate(self.client, self.get_logger())
        self.button = Button(self.client, self.get_logger())

    def demo_sequence(self):
        self.get_logger().info('\n===== DEMO SEQUENCE =====')
        self.gripper.open()
        time.sleep(1.0)
        self.arm.move_to_pose(0.30, 0.0, 0.20)
        time.sleep(2.0)
        self.arm.move_to_pose(0.25, 0.0, 0.35)
        time.sleep(2.0)
        self.arm.move_to_pose(0.25, -0.15, 0.25)
        time.sleep(2.0)
        self.gripper.close()
        time.sleep(1.0)
        self.arm.move_to_pose(0.25, 0.0, 0.25)
        time.sleep(2.0)
        self.gripper.open()
        time.sleep(1.0)
        self.arm.move_to_pose(0.15, 0.0, 0.10)
        self.get_logger().info('===== DEMO COMPLETE =====\n')

    def destroy(self):
        self.arm.cleanup()
        self.client.terminate()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)

    import argparse
    parser = argparse.ArgumentParser(
        prog='helix_control',
        description='Control the Helix robot via rosbridge: poses, tendons, '
                    'gripper, calibration, LED and trajectory demos.',
        usage='%(prog)s <action> [args...] [options]',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_EPILOG)
    parser.add_argument('action', nargs='?', default='info',
                        choices=list(ACTIONS),
                        help='Action to perform (details and examples below)')
    parser.add_argument('args', nargs='*',
                        help='Action arguments (see examples below)')
    parser.add_argument('--host', default=None,
                        help='Robot rosbridge host (default: from helix_config.yaml)')
    parser.add_argument('--port', type=int, default=None,
                        help='Robot rosbridge port (default: from helix_config.yaml)')
    parser.add_argument('--rate', type=float, default=50.0,
                        help='Streaming publish rate in Hz (default: %(default)s)')

    argv = rclpy.utilities.remove_ros_args(args or sys.argv)
    parsed = parser.parse_args(argv[1:])

    try:
        node = HelixControl(host=parsed.host, port=parsed.port)
    except ConfigError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)

    ACTIONS[parsed.action](node, parsed.args, parsed.rate)

    node.destroy()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
