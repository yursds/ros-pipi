# helix_comm

ROS 2 package to communicate with a [Helix robot](https://github.com/eai-ag)
via rosbridge: command the arm, gripper, tendons and LED, bridge robot
topics to native ROS 2, and inspect what the robot exposes.

## Table of Contents

- [Structure](#structure)
- [Build & Install](#build--install)
- [First Setup: Robot Address](#first-setup-robot-address)
- [Tools](#tools)
- [Documentation](#documentation)

## Structure

```text
helix_comm/
├── package.xml, setup.py, setup.cfg   # ament_python packaging
├── resource/                          # ament index resource marker
├── README.md                          # this file
└── helix_comm/
    ├── cli.py            # helix_control - unified command-line interface
    ├── bridge.py         # helix_bridge - rosbridge -> native ROS 2 topic bridge
    ├── helix_client.py   # helix_client - low-level rosbridge client
    ├── helix_info.py     # helix_info - robot info & diagnostics
    ├── actions.py        # action handlers backing the CLI
    ├── utils/            # shared helper modules
    │   ├── config_loader.py  # loads helix_config.yaml (host/port)
    │   └── help_text.py      # CLI help/epilog text
    └── control/          # device control modules
        ├── arm.py        #   cartesian / configuration / tendon control
        ├── gripper.py    #   open / close / set position
        ├── calibrate.py  #   tendon calibration management
        └── button.py     #   LED color control
```

## Build & Install

```bash
colcon build --packages-select helix_comm
source install/setup.bash
```

## First Setup: Robot Address

All tools **refuse to start until the robot address is configured** - there
are **no default values**. Create `src/config/helix_config.yaml`:

```yaml
host: 192.168.238.104   # replace with your robot's IP
port: 9090              # rosbridge WebSocket port
```

If the file is missing or incomplete, the tools exit with a clear error
explaining what to add. The file is searched via the `HELIX_CONFIG` env var,
or `src/config/helix_config.yaml` relative to the working directory.
`--host` / `--port` flags override it per-command.

## Tools

| Tool | Purpose |
| --- | --- |
| `helix_info` | One-shot check: connection status + every topic/service the robot exposes, then exits |
| `helix_client` | Same listing, stays connected - useful as a building block for other tools |
| `helix_bridge` | Bridges robot topics and `std_srvs/Trigger` services to native ROS 2, for PlotJuggler and the ROS 2 CLI |
| `helix_control` | Commands the robot (poses, tendons, gripper, calibration, LED) |

Quick start:

```bash
ros2 run helix_comm helix_control --help
ros2 run helix_comm helix_control home       # back to default position
ros2 run helix_comm helix_control demo       # gripper + pose demo sequence
ros2 run helix_comm helix_bridge             # bridge topics for PlotJuggler
ros2 run helix_comm helix_info               # what the robot actually exposes
```

## Documentation

The repo-level [`docs/`](../docs/) folder explains where to find the
robot's interface reference and how to view its topics and services:

- [`docs/README.md`](../docs/README.md) - overview: official references,
  local tools and how the pieces connect
- [`docs/topics_and_services.md`](../docs/topics_and_services.md) -
  complete inventory of the robot's topics and services, with types,
  descriptions and how to plot or call each one

The authoritative source is the official
[`eai-ag/ros-helix`](https://github.com/eai-ag/ros-helix) repository
(`Topics_and_Services.md` and the userguides); `helix_info` prints the
definitive list for your robot.
