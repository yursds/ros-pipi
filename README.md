# ros-pipi

ROS 2 packages for controlling a Helix robot via rosbridge.

## Packages

- `helix_comm` — CLI + bridge per Helix robot control
  - `cli` — unified command-line interface (`helix_control`)
  - `bridge` — rosbridge → native ROS 2 topic bridge (per PlotJuggler)
  - `helix_client` — low-level rosbridge client
  - `helix_info` — robot info & diagnostics
  - `config_loader` — loads `helix_config.yaml` (host/port)
  - `control/` — device control modules
    - `arm` — cartesian/configuration/tendon control
    - `gripper` — open/close/set position
    - `calibrate` — tendon calibration management
    - `button` — LED color control

## First Setup: Robot Address

All tools **refuse to start until the robot address is configured** — there
are **no default values**. Create `src/config/helix_config.yaml`:

```yaml
host: 192.168.238.104   # replace with your robot's IP
port: 9090              # rosbridge WebSocket port
```

If the file is missing or incomplete, the tools exit with a clear error
explaining what to add. The file is searched via the `HELIX_CONFIG` env var,
or `src/config/helix_config.yaml` relative to the working directory.
`--host` / `--port` flags override it per-command.

## Quick Start

```bash
colcon build --packages-select helix_comm
source install/setup.bash

ros2 run helix_comm helix_control --help
ros2 run helix_comm helix_control home       # back to default position
ros2 run helix_comm helix_bridge             # bridge topics for PlotJuggler
```
