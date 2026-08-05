"""Action handlers for the helix_control CLI, one function per action."""

import math
import time

import rclpy

from helix_comm.control.button import BUTTON_COLORS


def _publish_loop(node, publish, description, rate, duration=None, quiet=False):
    period = 1.0 / rate
    if not quiet:
        suffix = f" for {duration:.0f}s" if duration else ""
        node.get_logger().info(
            f"Streaming {description} at {rate:.1f} Hz{suffix} (Ctrl+C to stop)..."
        )
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
        if not quiet:
            node.get_logger().info(f"Streaming {description} stopped")


def do_info(node, args, rate):
    node.get_logger().info(
        "Connected. Run with --help to see all commands and examples."
    )
    rclpy.spin(node)


def do_open(node, args, rate):
    node.gripper.open()


def do_close(node, args, rate):
    node.gripper.close()


def do_demo(node, args, rate):
    node.demo_sequence()


def _parse_pairs(args):
    names, values = [], []
    for arg in args:
        if ":" in arg:
            name, val = arg.rsplit(":", 1)
            names.append(name)
            values.append(float(val))
    return names, values


def do_home(node, args, rate):
    hold = float(args[0]) if args else 3.0
    nominal = [0.125] * 3 + [0.25] * 6
    tendon_names = [f"tendon{i}" for i in range(9)]
    node.get_logger().info(
        f"Home: streaming all tendons to nominal length for {hold:.0f}s "
        "(straight position)..."
    )
    _publish_loop(
        node,
        lambda: node.arm.set_tendon_lengths(tendon_names, nominal),
        "home (nominal tendon lengths)",
        rate,
        duration=hold,
    )


def do_pose(node, args, rate):
    vals = [float(v) for v in args]
    if len(vals) < 3:
        node.get_logger().error("Usage: pose x y z [qx qy qz qw]")
    else:
        quat = vals[3:7] if len(vals) >= 7 else [0.0, 0.0, 0.0, 1.0]
        _publish_loop(
            node,
            lambda: node.arm.move_to_pose(vals[0], vals[1], vals[2], *quat),
            f"pose ({vals[0]:.3f}, {vals[1]:.3f}, {vals[2]:.3f})",
            rate,
        )


def do_config(node, args, rate):
    names, values = _parse_pairs(args)
    if names:
        _publish_loop(
            node,
            lambda: node.arm.set_configuration(names, values),
            f"configuration {dict(zip(names, values))}",
            rate,
        )


def do_tendon(node, args, rate):
    names, values = _parse_pairs(args)
    if names:
        _publish_loop(
            node,
            lambda: node.arm.set_tendon_lengths(names, values),
            f"tendon lengths {dict(zip(names, values))}",
            rate,
        )


def do_calibrate(node, args, rate):
    sub = args[0] if args else "status"
    if sub == "status":
        node.calibrate.status()
    elif sub == "current":
        if len(args) >= 2:
            node.calibrate.set_current(float(args[1]))
        else:
            node.calibrate.status()
    elif sub == "start":
        node.calibrate.start()
    elif sub == "finish":
        node.calibrate.finish()
    elif sub == "limits":
        node.calibrate.compression_limits()
    else:
        node.get_logger().error(f"Unknown calibrate subcommand: {sub}")


def do_circle(node, args, rate):
    cx = float(args[0]) if len(args) > 0 else 0.0
    cy = float(args[1]) if len(args) > 1 else 0.0
    r = float(args[2]) if len(args) > 2 else 0.10
    z = float(args[3]) if len(args) > 3 else 0.50
    period = (
        float(args[4]) if len(args) > 4 else 16.0
    )  # seconds per lap (robot is slow)
    t0 = node.get_clock().now()
    node.get_logger().info(
        f"Circle: center=({cx:.3f}, {cy:.3f})  r={r:.3f}  z={z:.3f}  "
        f"period={period:.0f}s  rate={rate:.1f} Hz"
    )

    def _publish():
        # Time-based trajectory: theta = 2*pi * t / period (dt = 1/rate)
        t = (node.get_clock().now() - t0).nanoseconds * 1e-9
        theta = 2.0 * math.pi * t / period
        node.arm.move_to_pose(cx + r * math.cos(theta), cy + r * math.sin(theta), z)

    _publish_loop(
        node, _publish, f"circle center=({cx:.3f}, {cy:.3f}) r={r:.3f} z={z:.3f}", rate
    )


def do_circle_tendon(node, args, rate):
    amplitude = float(args[0]) if len(args) > 0 else 0.05
    period = float(args[1]) if len(args) > 1 else 16.0
    modules = int(args[2]) if len(args) > 2 else 1
    n_tendons = modules * 3
    tendon_names = [f"tendon{i}" for i in range(n_tendons)]
    # straight length = segment length in meters
    straight = [0.125] * 3 + [0.25] * 6
    bases_mod = straight[:n_tendons]
    amps_mod = [amplitude] * n_tendons
    phases = ([0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0] * modules)[:n_tendons]
    t0 = node.get_clock().now()
    node.get_logger().info(
        f"Circle tendon: {modules} module(s)  amp={amplitude:.3f}  "
        f"period={period:.1f}s  rate={rate:.1f} Hz"
    )

    def _publish():
        # Time-based trajectory: theta = 2*pi * t / period (dt = 1/rate)
        t = (node.get_clock().now() - t0).nanoseconds * 1e-9
        theta = 2.0 * math.pi * t / period
        node.arm.set_tendon_lengths(
            tendon_names,
            [
                b - a * (1.0 - math.cos(theta + p)) / 2.0
                for b, a, p in zip(bases_mod, amps_mod, phases)
            ],
        )

    _publish_loop(
        node, _publish, f"circle tendon {modules} module(s) amp={amplitude:.3f}", rate
    )


def do_tendon_demo(node, args, rate):
    amplitude = float(args[0]) if len(args) > 0 else 0.015
    hold = float(args[1]) if len(args) > 1 else 3.0
    nominal = [0.125] * 3 + [0.25] * 6
    tendon_names = [f"tendon{i}" for i in range(9)]
    node.get_logger().info(
        f"Tendon demo: 9 tendons one at a time, amplitude={amplitude:.3f} m, "
        f"hold={hold:.0f} s each"
    )
    node.get_logger().info("-- Moving to default position (all tendons nominal)...")
    _publish_loop(
        node,
        lambda: node.arm.set_tendon_lengths(tendon_names, nominal),
        "default position (nominal tendon lengths)",
        rate,
        duration=hold,
        quiet=True,
    )
    if not rclpy.ok():
        node.get_logger().info("Tendon demo interrupted")
        return
    for name, base in zip(tendon_names, nominal):
        node.get_logger().info(f"-- {name}: {base:.3f} -> {base - amplitude:.3f}")
        _publish_loop(
            node,
            lambda n=name, v=base - amplitude: node.arm.set_tendon_lengths([n], [v]),
            f"{name} = {base - amplitude:.3f}",
            rate,
            duration=hold,
            quiet=True,
        )
        if not rclpy.ok():
            break
        node.get_logger().info(f"-- {name}: back to {base:.3f}")
        _publish_loop(
            node,
            lambda n=name, v=base: node.arm.set_tendon_lengths([n], [v]),
            f"{name} = {base:.3f}",
            rate,
            duration=hold,
            quiet=True,
        )
        if not rclpy.ok():
            break
    if rclpy.ok():
        node.get_logger().info("===== TENDON DEMO COMPLETE =====")
    else:
        node.get_logger().info("Tendon demo interrupted")


def do_button(node, args, rate):
    if not args:
        node.get_logger().info(f"Colors: {', '.join(BUTTON_COLORS)}")
    elif args[0] in BUTTON_COLORS:
        r, g, b = BUTTON_COLORS[args[0]]
        node.button.set_color(r, g, b)
    elif len(args) >= 3:
        node.button.set_color(*args[:3])
    else:
        node.get_logger().error("Usage: button <color> | button <r> <g> <b>")


ACTIONS = {
    "button": do_button,
    "calibrate": do_calibrate,
    "circle": do_circle,
    "circle_tendon": do_circle_tendon,
    "close": do_close,
    "config": do_config,
    "demo": do_demo,
    "home": do_home,
    "info": do_info,
    "open": do_open,
    "pose": do_pose,
    "tendon": do_tendon,
    "tendon_demo": do_tendon_demo,
}
