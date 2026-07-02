# DogCopter

Simulation workspace for **DogCopter** — a robot dog that transforms into a
drone to fly over obstacles it can't walk past. Built on ROS 2 Humble,
Gazebo Harmonic, PX4 SITL (standalone mode), and Nav2.

Current test vehicle: a diff-drive "onboarding bot" base with an x500
quadrotor mounted on top. It **drives on the ground and flies with PX4 in
the same Gazebo session** (verified drive → fly → drive). The Unitree Go2
quadruped will replace the wheeled base later.

## Packages

| Package | What it is |
|---|---|
| `flight_robot_pkg` | The hybrid drive-and-fly vehicle: Gazebo model, PX4 airframe (`4030_gz_flight_robot`), symlink setup scripts, standalone-Gazebo launcher. See `flight_robot_pkg/DEBUGGING_GUIDE.md` for how to run and tune. |
| `my_robot_description` | URDF/xacro of the ground-only onboarding bot (diff drive + 2D lidar). |
| `my_robot_bringup` | Launch files, worlds, and the ros_gz bridge config for the ground-only bot. |
| `my_cpp_pkg` | ROS 2 C++ starter/example package. |

## Prerequisites

- ROS 2 Humble, Gazebo Harmonic (`gz`), `ros_gz` packages
- PX4-Autopilot cloned at `~/PX4-Autopilot` (v1.16.x) and built:
  `make px4_sitl_default`
- PX4 stays **unmodified** — this repo symlinks its model and airframe
  into the PX4 tree: `bash flight_robot_pkg/flight_robot_pkg/launch/link_setup.sh`

## Quick start (hybrid vehicle)

```bash
# Terminal 1 — Gazebo
python3 flight_robot_pkg/flight_robot_pkg/launch/simulation-gazebo.py --world default

# Terminal 2 — PX4 standalone
cd ~/PX4-Autopilot
PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4030 PX4_SIM_MODEL=gz_flight_robot \
PX4_GZ_MODELS=$HOME/PX4-Autopilot/Tools/simulation/gz/models \
./build/px4_sitl_default/bin/px4
```

Then in the pxh shell: `commander takeoff` / `commander land`
(connect QGroundControl, or `param set NAV_DLL_ACT 0` when running headless).

## Roadmap

- [x] **M1 — Stable flight**: hybrid model takes off, hovers, lands
  (fixed July 2026; root causes documented in the debugging guide)
- [x] **M1.5 — Ground driving**: DiffDrive works on the same model
- [ ] **M2 — ROS bridge for the hybrid**: bridge `cmd_vel` / `odom` /
  `joint_states` so the hybrid drives from ROS 2 (teleop), modeled on
  `my_robot_bringup/config/gazebo_bridge.yaml`
- [ ] **M3 — Mode arbitration**: GROUND/FLIGHT state node (ROS service).
  GROUND forwards `/cmd_vel` to wheels and refuses arming; FLIGHT zeroes
  wheels and hands control to PX4 via Micro XRCE-DDS + `px4_msgs`.
  Demo: drive → transform → fly over obstacle → land → drive.
- [ ] **M4 — Lidar + Nav2**: mount the lidar from `my_robot_description`
  on the hybrid, autonomous A→B navigation in GROUND mode
- [ ] **M5 — Go2 quadruped base** (large effort — ros2_control +
  champ-style gait controllers in Gazebo Harmonic; the wheeled base
  remains the flight-test proxy until then. Design M3 so the locomotion
  backend is swappable.)

## Notes

- The local `~/PX4-Autopilot` checkout may contain unrelated experiments
  (e.g. `4001_gz_test_drone`); this repo does not depend on them.
- "Bigger propellers / more lift" in simulation = scaling `motorConstant`
  and rotor geometry in `model.sdf` + matching `CA_ROTOR*` params in the
  airframe — no CAD needed until a real airframe exists.
