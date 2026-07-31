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


def _publish_loop(node, publish, description, rate, duration=None):
    """Re-publish a command at a fixed rate.

    Streams until Ctrl+C, or for `duration` seconds when given.
    A ROS 2 timer drives the publishing rate (no sleep).
    """
    period = 1.0 / rate
    node.get_logger().info(
        f'Streaming {description} at {rate:.1f} Hz'
        + (f' for {duration:.0f}s' if duration else '')
        + ' (Ctrl+C to stop)...')
    timer = node.create_timer(period, publish)
    deadline = time.monotonic() + duration if duration is not None else None
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            if deadline is not None and time.monotonic() >= deadline:
                break
    except KeyboardInterrupt:
        pass
    finally:
        timer.cancel()
        node.get_logger().info(f'Streaming {description} stopped')


HELP_EPILOG = """
ACTIONS AND ARGUMENTS
---------------------
  info                     Show connection info and available commands.
  demo                     Run the demo sequence (gripper + poses).
  open | close             Open / close the gripper.

  pose  X Y Z [QX QY QZ QW]
                           Move the end-effector to a cartesian pose.
                           X Y Z in meters; QX..QW is an optional quaternion.
                           Streamed until Ctrl+C.

  config NAME:VALUE [...]
                           Set joint configuration values.
                           Streamed until Ctrl+C.

  tendon NAME:VALUE [...]
                           Set tendon lengths in meters.
                           Names: tendon0 .. tendon8
                           (tendon0-2 = module 1, tendon3-5 = module 2,
                            tendon6-8 = module 3; straight robot = 0.125 /
                            0.25).
                           Streamed until Ctrl+C.

  calibrate [status | current N | start | finish | limits]
                           Tendon calibration management.

  button [COLOR | R G B]
                           Set the LED color. Colors: green, red, blue,
                           yellow, white, ... or explicit RGB values 0-255.

  circle [CX CY R Z PERIOD STEPS]
                           Trace a circle with the end-effector.
                           CX CY: center of the circle in meters (default 0 0)
                           R:     radius in meters (default 0.10)
                           Z:     height in meters (default 0.50)
                           PERIOD: seconds per lap (default 16)
                           STEPS:  points per lap (default 800 = 50 Hz)
                           Streamed until Ctrl+C.

  circle_tendon [AMPLITUDE PERIOD STEPS MODULES]
                           Trace a circle by oscillating the tendons of
                           one or two modules.
                           AMPLITUDE: tendon range in meters (default 0.05;
                           use small values like 0.015 for a gentle motion)
                           PERIOD: seconds per lap (default 16)
                           STEPS:  points per lap (default 800 = 50 Hz)
                           MODULES: 1 or 2 (default 1)
                           Streamed until Ctrl+C.

  tendon_demo [AMPLITUDE HOLD]
                           Move one tendon at a time (tendon0 .. tendon8).
                           Always starts from the default position: all
                           tendons are streamed back to their nominal
                           length first. Then, for each tendon: shorten it
                           by AMPLITUDE (default 0.015 m), hold HOLD
                           seconds (default 3), then return to the
                           straight length. Useful to check each motor
                           individually. Interrupt with Ctrl+C at any time.

EXAMPLES
--------
  helix_control info
  helix_control demo
  helix_control pose 0.10 0.0 0.55
  helix_control tendon tendon0:0.125 tendon1:0.125 tendon2:0.125
  helix_control circle 0.0 0.0 0.10 0.50 16 800
  helix_control circle_tendon 0.015 16 800 1
  helix_control tendon_demo
  helix_control button green
  helix_control calibrate status

STREAMING
---------
pose, config, tendon, circle and circle_tendon keep sending the command
at --rate Hz until you press Ctrl+C. The robot controller reacts
slowly, so a single command is often ignored: streaming is required
to make the robot move. Lower --rate for slower, smoother motion.
"""


def main(args=None):
    rclpy.init(args=args)

    import argparse
    cfg = load_config()
    parser = argparse.ArgumentParser(
        prog='helix_control',
        description='Control the Helix robot via rosbridge.',
        usage='%(prog)s <action> [args...] [options]',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_EPILOG)
    parser.add_argument('action', nargs='?', default='info',
                        choices=['info', 'demo', 'open', 'close',
                                 'pose', 'config', 'tendon', 'calibrate', 'button',
                                 'circle', 'circle_tendon', 'tendon_demo'],
                        help='Action to perform (details and examples below)')
    parser.add_argument('args', nargs='*',
                        help='Action arguments (see examples below)')
    parser.add_argument('--host', default=cfg['host'],
                        help='Robot rosbridge host (default: %(default)s)')
    parser.add_argument('--port', type=int, default=cfg['port'],
                        help='Robot rosbridge port (default: %(default)s)')
    parser.add_argument('--rate', type=float, default=50.0,
                        help='Streaming publish rate in Hz (default: %(default)s)')

    argv = rclpy.utilities.remove_ros_args(args or sys.argv)
    parsed = parser.parse_args(argv[1:])

    node = HelixControl()

    if parsed.action == 'info':
        node.get_logger().info(
            'Connected. Run with --help to see all commands and examples.')
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
            _publish_loop(
                node,
                lambda: node.arm.move_to_pose(vals[0], vals[1], vals[2], *quat),
                f'pose ({vals[0]:.3f}, {vals[1]:.3f}, {vals[2]:.3f})',
                parsed.rate)

    elif parsed.action == 'config':
        names, values = [], []
        for arg in parsed.args:
            if ':' in arg:
                name, val = arg.rsplit(':', 1)
                names.append(name)
                values.append(float(val))
        if names:
            _publish_loop(
                node,
                lambda: node.arm.set_configuration(names, values),
                f'configuration {dict(zip(names, values))}',
                parsed.rate)

    elif parsed.action == 'tendon':
        names, values = [], []
        for arg in parsed.args:
            if ':' in arg:
                name, val = arg.rsplit(':', 1)
                names.append(name)
                values.append(float(val))
        if names:
            _publish_loop(
                node,
                lambda: node.arm.set_tendon_lengths(names, values),
                f'tendon lengths {dict(zip(names, values))}',
                parsed.rate)

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
        cx = float(parsed.args[0]) if len(parsed.args) > 0 else 0.0
        cy = float(parsed.args[1]) if len(parsed.args) > 1 else 0.0
        r = float(parsed.args[2]) if len(parsed.args) > 2 else 0.10
        z = float(parsed.args[3]) if len(parsed.args) > 3 else 0.50
        period = float(parsed.args[4]) if len(parsed.args) > 4 else 16.0   # seconds per lap (robot is slow)
        steps = int(parsed.args[5]) if len(parsed.args) > 5 else 800       # points per lap (50 Hz @ 16 s)
        rate = steps / period   # publish rate in Hz (ROS rate, no sleep)
        node.get_logger().info(
            f'Circle: center=({cx:.3f}, {cy:.3f})  r={r:.3f}  z={z:.3f}  '
            f'period={period:.0f}s  steps={steps}  rate={rate:.1f} Hz'
        )

        def _circle_points():
            while True:
                for i in range(steps):
                    theta = 2.0 * math.pi * i / steps
                    yield (cx + r * math.cos(theta),
                           cy + r * math.sin(theta), z)

        points = _circle_points()

        def _publish():
            node.arm.move_to_pose(*next(points))

        _publish_loop(node, _publish,
                      f'circle center=({cx:.3f}, {cy:.3f}) r={r:.3f} z={z:.3f}',
                      rate)

    elif parsed.action == 'circle_tendon':
        import math
        amplitude = float(parsed.args[0]) if len(parsed.args) > 0 else 0.05
        period = float(parsed.args[1]) if len(parsed.args) > 1 else 16.0
        steps = int(parsed.args[2]) if len(parsed.args) > 2 else 800       # points per lap (50 Hz @ 16 s)
        modules = int(parsed.args[3]) if len(parsed.args) > 3 else 1
        n_tendons = modules * 3
        tendon_names = [f'tendon{i}' for i in range(n_tendons)]
        # straight length = segment length in meters
        straight = [0.125] * 3 + [0.25] * 6
        bases_mod = straight[:n_tendons]
        amps_mod = [amplitude] * n_tendons
        phases = ([0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0] * modules)[:n_tendons]
        rate = steps / period   # publish rate in Hz (ROS rate, no sleep)
        node.get_logger().info(
            f'Circle tendon: {modules} module(s)  amp={amplitude:.3f}  '
            f'period={period:.1f}s  steps={steps}  rate={rate:.1f} Hz'
        )

        def _tendon_sequence():
            while True:
                for i in range(steps):
                    theta = 2.0 * math.pi * i / steps
                    yield [b - a * (1.0 - math.cos(theta + p)) / 2.0
                           for b, a, p in zip(bases_mod, amps_mod, phases)]

        seq = _tendon_sequence()

        def _publish():
            node.arm.set_tendon_lengths(tendon_names, next(seq))

        _publish_loop(node, _publish,
                      f'circle tendon {modules} module(s) amp={amplitude:.3f}',
                      rate)

    elif parsed.action == 'tendon_demo':
        amplitude = float(parsed.args[0]) if len(parsed.args) > 0 else 0.015
        hold = float(parsed.args[1]) if len(parsed.args) > 1 else 3.0
        nominal = [0.125] * 3 + [0.25] * 6
        tendon_names = [f'tendon{i}' for i in range(9)]
        node.get_logger().info(
            f'Tendon demo: 9 tendons one at a time, amplitude={amplitude:.3f} m, '
            f'hold={hold:.0f} s each')
        # Always start from the default (straight) position: stream all
        # tendons back to their nominal length before touching any motor.
        node.get_logger().info(
            '-- Moving to default position (all tendons nominal)...')
        _publish_loop(
            node,
            lambda: node.arm.set_tendon_lengths(tendon_names, nominal),
            'default position (nominal tendon lengths)', parsed.rate,
            duration=hold)
        if not rclpy.ok():
            node.get_logger().info('Tendon demo interrupted')
            return
        for name, base in zip(tendon_names, nominal):
            node.get_logger().info(
                f'-- {name}: {base:.3f} -> {base - amplitude:.3f}')
            _publish_loop(
                node,
                lambda n=name, v=base - amplitude:
                    node.arm.set_tendon_lengths([n], [v]),
                f'{name} = {base - amplitude:.3f}', parsed.rate, duration=hold)
            if not rclpy.ok():
                break
            node.get_logger().info(
                f'-- {name}: back to {base:.3f}')
            _publish_loop(
                node,
                lambda n=name, v=base:
                    node.arm.set_tendon_lengths([n], [v]),
                f'{name} = {base:.3f}', parsed.rate, duration=hold)
            if not rclpy.ok():
                break
        if rclpy.ok():
            node.get_logger().info('===== TENDON DEMO COMPLETE =====')
        else:
            node.get_logger().info('Tendon demo interrupted')

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
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
