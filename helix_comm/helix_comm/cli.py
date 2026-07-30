#!/usr/bin/env python3
"""CLI to control the Helix robot via rosbridge."""

import sys
import time
import rclpy
from rclpy.node import Node
import roslibpy

from helix_comm.arm import Arm
from helix_comm.gripper import Gripper
from helix_comm.calibrate import Calibrate
from helix_comm.button import Button, BUTTON_COLORS
from helix_comm.config_loader import load_config


class HelixControl(Node):
    def __init__(self):
        super().__init__('helix_control')
        cfg = load_config()
        self.declare_parameter('host', cfg['host'])
        self.declare_parameter('port', cfg['port'])

        host = self.get_parameter('host').value
        port = self.get_parameter('port').value

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
    cfg = load_config()
    parser = argparse.ArgumentParser(description='Control Helix robot')
    parser.add_argument('action', nargs='?', default='info',
                        choices=['info', 'demo', 'open', 'close',
                                 'pose', 'config', 'tendon', 'calibrate', 'button',
                                 'circle'],
                        help='Action to perform')
    parser.add_argument('args', nargs='*', help='Additional arguments')
    parser.add_argument('--host', default=cfg['host'])
    parser.add_argument('--port', type=int, default=cfg['port'])

    argv = rclpy.utilities.remove_ros_args(args or sys.argv)
    parsed = parser.parse_args(argv[1:])

    node = HelixControl()

    if parsed.action == 'info':
        node.get_logger().info('Connected. open | close | demo | pose x y z [qx qy qz qw]')
        rclpy.spin(node)

    elif parsed.action == 'open':
        node.gripper.open()

    elif parsed.action == 'close':
        node.gripper.close()

    elif parsed.action == 'demo':
        node.demo_sequence()

    elif parsed.action == 'pose':
        vals = [float(v) for v in parsed.args]
        if len(vals) < 3:
            node.get_logger().error('Usage: pose x y z [qx qy qz qw]')
        else:
            quat = vals[3:7] if len(vals) >= 7 else [0.0, 0.0, 0.0, 1.0]
            node.arm.move_to_pose(vals[0], vals[1], vals[2], *quat)

    elif parsed.action == 'config':
        names, values = [], []
        for arg in parsed.args:
            if ':' in arg:
                name, val = arg.rsplit(':', 1)
                names.append(name)
                values.append(float(val))
        if names:
            node.arm.set_configuration(names, values)

    elif parsed.action == 'tendon':
        names, values = [], []
        for arg in parsed.args:
            if ':' in arg:
                name, val = arg.rsplit(':', 1)
                names.append(name)
                values.append(float(val))
        if names:
            node.arm.set_tendon_lengths(names, values)

    elif parsed.action == 'calibrate':
        sub = parsed.args[0] if parsed.args else 'status'
        if sub == 'status':
            node.calibrate.status()
        elif sub == 'current':
            if len(parsed.args) >= 2:
                node.calibrate.set_current(float(parsed.args[1]))
            else:
                node.calibrate.status()
        elif sub == 'start':
            node.calibrate.start()
        elif sub == 'finish':
            node.calibrate.finish()
        elif sub == 'limits':
            node.calibrate.compression_limits()
        else:
            node.get_logger().error(f'Unknown calibrate subcommand: {sub}')

    elif parsed.action == 'circle':
        import math
        cx = float(parsed.args[0]) if len(parsed.args) > 0 else 0.30
        cy = float(parsed.args[1]) if len(parsed.args) > 1 else 0.0
        r = float(parsed.args[2]) if len(parsed.args) > 2 else 0.10
        z = float(parsed.args[3]) if len(parsed.args) > 3 else 0.50
        period = float(parsed.args[4]) if len(parsed.args) > 4 else 120.0  # seconds per lap
        steps = int(parsed.args[5]) if len(parsed.args) > 5 else 240       # points per lap
        node.get_logger().info(
            f'Circle: center=({cx:.3f}, {cy:.3f})  r={r:.3f}  z={z:.3f}  '
            f'period={period:.0f}s  steps={steps}'
        )
        delay = period / steps
        node.get_logger().info('Starting circle (Ctrl+C to stop)...')
        try:
            while True:
                for i in range(steps):
                    theta = 2.0 * math.pi * i / steps
                    x = cx + r * math.cos(theta)
                    y = cy + r * math.sin(theta)
                    node.arm.move_to_pose(x, y, z)
                    time.sleep(delay)
        except KeyboardInterrupt:
            node.get_logger().info('Circle stopped')

    elif parsed.action == 'button':
        if not parsed.args:
            node.get_logger().info(f'Colors: {", ".join(BUTTON_COLORS)}')
        elif parsed.args[0] in BUTTON_COLORS:
            r, g, b = BUTTON_COLORS[parsed.args[0]]
            node.button.set_color(r, g, b)
        elif len(parsed.args) >= 3:
            node.button.set_color(*parsed.args[:3])
        else:
            node.get_logger().error('Usage: button <color> | button <r> <g> <b>')

    node.destroy()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
