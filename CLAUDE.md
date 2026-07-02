# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Simulation workspace for DogCopter: a hybrid vehicle that drives on the ground (diff-drive) and flies (PX4 quadrotor) in the same Gazebo session. This repo is the `src/` of a colcon workspace (`~/ros2_ws`). Stack: ROS 2 Humble, **Gazebo Harmonic only** (all plugins are `gz::sim::systems::*` / `ros_gz` — never add Gazebo Classic `libgazebo_ros_*` plugins), PX4 SITL v1.16.x in **standalone mode**, Nav2 planned.

## Commands

```bash
# Build (from the workspace root, not src/)
cd ~/ros2_ws && colcon build && source install/setup.bash

# One-time after clone/move: symlink model + airframe into the PX4 tree
bash flight_robot_pkg/flight_robot_pkg/launch/link_setup.sh

# Run the hybrid vehicle — two terminals:
python3 flight_robot_pkg/flight_robot_pkg/launch/simulation-gazebo.py --world default   # add --headless on servers
cd ~/PX4-Autopilot && PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4030 PX4_SIM_MODEL=gz_flight_robot \
  PX4_GZ_MODELS=$HOME/PX4-Autopilot/Tools/simulation/gz/models ./build/px4_sitl_default/bin/px4

# Flight test (pxh shell, or px4-commander/px4-listener/px4-param client binaries from another shell)
commander takeoff / commander land
param set NAV_DLL_ACT 0        # runtime-only: bypass no-GCS arming block when headless; never bake into the airframe
listener actuator_motors       # hover ≈ 0.55–0.65, all four symmetric; visual prop speed is meaningless (rotorVelocitySlowdownSim)

# Ground driving of the hybrid (no ROS bridge yet)
gz topic -t /model/flight_robot_0/cmd_vel -m gz.msgs.Twist -p 'linear: {x: 0.5}'

# Ground-only bot
ros2 launch my_robot_bringup my_robot_gazebo.launch.py

# Validate an SDF after editing (SDF_PATH needed to resolve model:// includes)
SDF_PATH=$HOME/.simulation-gazebo/models gz sdf --check flight_robot_pkg/flight_robot_pkg/models/flight_robot/model.sdf
```

There is no test suite beyond the stock ament lint tests; verification is running the sim (success criteria: model rests level on its wheels, 30 s+ hover with symmetric motor outputs, clean land + auto-disarm).

## Architecture

Two parallel robot stacks that will converge:

- **Ground-only onboarding bot** — `my_robot_description` (URDF/xacro: diff drive, 2D gpu_lidar) + `my_robot_bringup` (launch, worlds, `config/gazebo_bridge.yaml` for ros_gz topic bridging). This is the template for adding ROS bridging/Nav2 to the hybrid.
- **Hybrid flight vehicle** — `flight_robot_pkg`. Pure SDF (no URDF), spawned by PX4's gz_bridge, driven by PX4 + the Gazebo DiffDrive plugin.

### PX4 integration pattern (the load-bearing design)

The PX4 tree at `~/PX4-Autopilot` is **never modified**; `link_setup.sh` symlinks this repo's model dir and airframe into it (including into `build/.../rootfs`). Consequences:
- Airframe edits need **no PX4 rebuild** — the airframe is a shell script sourced at boot through the symlink.
- After changing airframe params, wipe cached params: `rm ~/PX4-Autopilot/build/px4_sitl_default/rootfs/parameters*.bson`.
- Always use `ln -sfn` for these links (`-f` alone dereferences an existing dir symlink and creates a recursive self-link).
- Airframe ID is **4030** (`airframes/4030_gz_flight_robot`). Do not use 4002 — it collides with stock `4002_gz_x500_depth` and rcS picks `${SYS_AUTOSTART}_*` matches by glob order.
- `PX4_GZ_MODELS` is **mandatory** in standalone mode (standalone doesn't source `gz_env.sh`; without it the spawn URI is broken and gz_bridge fails at boot).

### Model design constraints (`models/flight_robot/model.sdf`)

- `simulation-gazebo.py` hardcodes `GZ_SIM_RESOURCE_PATH=~/.simulation-gazebo/models`, so `model://` includes resolve to the **downloaded model store** — not copies in this repo or the PX4 tree. That is why `model.sdf` is deliberately self-contained: it includes only `model://x500_base` (geometry + sensors, zero tunables, identical in every copy) and **inlines the four MulticopterMotorModel plugins**. Never switch back to `model://x500` — motor edits would be silently ignored.
- The SDF and the airframe must stay in sync: `CA_ROTORn_PX/PY` = SDF rotor positions with the **y sign flipped** (SDF is FLU, PX4 is FRD); `CA_ROTORn_KM` magnitude = SDF `momentConstant` (change them together).
- Keep thrust-to-weight ≥ 2.0. Current budget: 3.41 kg total, motorConstant 2.0e-05 → 80 N, T/W ≈ 2.4. Adding payload (lidar etc.) means scaling `motorConstant` and re-trimming `MPC_THR_HOVER` to observed hover output. The mass table lives in `flight_robot_pkg/DEBUGGING_GUIDE.md` — keep it updated.
- A joint's `<pose>` places the joint frame, not the child link; the drone height is set by the `<pose>` **inside the include** (currently 0.35 m).

`flight_robot_pkg/DEBUGGING_GUIDE.md` is the runbook: post-mortem of the five bugs that caused the original takeoff crashes, boot sanity checks, and tuning levers with real PX4 param names. `README.md` has the milestone roadmap (next: M2 ROS bridge for the hybrid, M3 ground/flight mode arbitration via Micro XRCE-DDS + px4_msgs, M4 lidar + Nav2, M5 Go2 base — deferred; the wheeled base is the flight-test proxy).

Workflow: commit after every verified milestone and push to GitHub (repo: `dogcopter`); commit a baseline before risky changes. Legacy SDF variants in `models/flight_robot/` (`modified.sdf`, `my_robot.sdf`, `model_hybrid_recommended.sdf`) are historical — only `model.sdf` is live.
