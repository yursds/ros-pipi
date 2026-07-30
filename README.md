# ros-pipi

ROS 2 packages for controlling a Helix robot via rosbridge.

## Packages

- `helix_comm` — CLI + bridge per Helix robot control
  - `arm` — cartesian/configuration/tendon control
  - `gripper` — open/close/set position
  - `calibrate` — tendon calibration management
  - `button` — LED color control
  - `bridge` — rosbridge → native ROS 2 topic bridge (per PlotJuggler)
  - `cli` — unified command-line interface

## Quick Start

```bash
colcon build --packages-select helix_comm
source install/setup.bash

ros2 run helix_comm helix_control --help
ros2 run helix_comm helix_bridge           # bridge topics for PlotJuggler
```
