HELP_EPILOG = """
ACTIONS AND ARGUMENTS
---------------------
  button [COLOR | R G B]
                           Set the LED color. Colors: green, red, blue,
                           yellow, white, ... or explicit RGB values 0-255.

  calibrate [status | current N | start | finish | limits]
                           Tendon calibration management.

  circle [CX CY R Z PERIOD]
                           Trace a circle with the end-effector.
                           CX CY: center of the circle in meters (default 0 0)
                           R:     radius in meters (default 0.10)
                           Z:     height in meters (default 0.50)
                           PERIOD: seconds per lap (default 16)
                           The trajectory is a function of ROS time:
                           theta advances 2*pi per PERIOD, sampled at
                           --rate Hz. Streamed until Ctrl+C.

  circle_tendon [AMPLITUDE PERIOD MODULES]
                           Trace a circle by oscillating the tendons of
                           one or two modules.
                           AMPLITUDE: tendon range in meters (default 0.05;
                           use small values like 0.015 for a gentle motion)
                           PERIOD: seconds per lap (default 16)
                           MODULES: 1 or 2 (default 1)
                           The trajectory is a function of ROS time:
                           theta advances 2*pi per PERIOD, sampled at
                           --rate Hz. Streamed until Ctrl+C.

  config NAME:VALUE [...]
                           Set joint configuration values.
                           Streamed until Ctrl+C.

  demo                     Run the demo sequence (gripper + poses).

  home [HOLD]              Return to the default (straight) position.
                           Streams all tendons to their nominal length
                           for HOLD seconds (default 3).

  info                     Show connection info and available commands.

  open | close             Open / close the gripper.

  pose  X Y Z [QX QY QZ QW]
                           Move the end-effector to a cartesian pose.
                           X Y Z in meters; QX..QW is an optional quaternion.
                           Streamed until Ctrl+C.

  tendon NAME:VALUE [...]
                           Set tendon lengths in meters.
                           Names: tendon0 .. tendon8
                           (tendon0-2 = module 1, tendon3-5 = module 2,
                            tendon6-8 = module 3; straight robot = 0.125 /
                            0.25).
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
  helix_control button green
  helix_control calibrate status
  helix_control circle 0.0 0.0 0.10 0.50 16
  helix_control circle_tendon 0.015 16 1
  helix_control demo
  helix_control home
  helix_control info
  helix_control pose 0.10 0.0 0.55
  helix_control tendon tendon0:0.125 tendon1:0.125 tendon2:0.125
  helix_control tendon_demo

STREAMING
---------
pose, config, tendon, circle and circle_tendon keep sending the command
at --rate Hz until you press Ctrl+C. The robot controller reacts
slowly, so a single command is often ignored: streaming is required
to make the robot move. Lower --rate for slower, smoother motion.

home and tendon_demo stream for a bounded duration instead: they
publish their command for HOLD seconds (default 3) and stop
automatically, so no Ctrl+C is needed.
"""
