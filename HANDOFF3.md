# HANDOFF3 — DogCopter session handoff (2026-07-02)

## 1. GOAL

DogCopter is a university club project: a robot dog that transforms into a drone to fly over obstacles it can't walk past, then lands and walks again. The current phase is a comprehensive simulation (ROS 2 Humble + Gazebo Harmonic + PX4 SITL standalone + Nav2 later) using a wheeled "onboarding bot" base with an x500 quad on top as a stand-in for the eventual Unitree Go2 + custom drone. The immediate objective this session was: fix the crash-on-takeoff, put everything under git/GitHub, and establish the roadmap — all done.

## 2. CURRENT STATE

**Milestones 2 and 3 are done and verified (2026-07-02, second session).**
- M2: `flight_robot_bridge.launch.py` bridges cmd_vel/odom/joint_states/tf/clock; teleop_twist_keyboard drives the hybrid from ROS 2 (verified: 0.5 m/s → odom advanced 3 m). This fixed the user's "can't drive with cmd_vel" issue — there was simply no bridge.
- M3: `mode_manager` node + `flight_robot_bringup.launch.py`; drive → fly → drive commanded entirely from ROS 2 via `/dogcopter/set_flight_mode` (verified end-to-end: hover 2.47 m, teleop ignored in FLIGHT, auto-disarm on land, drove again). px4_msgs pinned to 431c15a in the workspace (gitignored). NEXT: **M4 — lidar + Nav2** (see README roadmap).

**Milestone 1 was achieved and verified in the first session** (headless sim):
- Hybrid vehicle takes off, hovers 35 s+ at 2.5 m with <5 cm drift, motor outputs symmetric at ~0.585, `commander land` touches down on wheels, auto-disarms.
- Ground driving works via the DiffDrive plugin (`gz topic` pub to cmd_vel; 0.5 m/s straight-line verified).
- Full **drive → fly → drive** cycle verified twice in one unbroken sim session.

**Git**: repo initialized at `/home/weichien241/ros2_ws/src` (branch `main`). Key commits:
```
fbb3faa Add HANDOFF3.md session handoff document
21542de Add CLAUDE.md with sim commands and PX4 integration constraints
8d75801 Milestone 1: hybrid vehicle hovers, lands, and drives
ebcab79 Fix hybrid flight model: thrust margin, control geometry, airframe ID
fd24b62 Baseline: DogCopter workspace before flight fixes
```

**GitHub**: DONE — pushed to https://github.com/WeiChien5241/dogcopter (public), `main` tracks `origin/main`. `gh` v2.63.2 lives at `~/.local/bin/gh`, authenticated as WeiChien5241. Push after every milestone: `git push`.

User decisions already made this session (do not re-ask): public repo "dogcopter"; gh CLI over SSH-remote; thrust fix = scale motors up AND lighten base ("Both" option).

## 3. KEY DECISIONS (do not re-litigate)

1. **Self-contained model.sdf.** `simulation-gazebo.py` hardcodes `GZ_SIM_RESOURCE_PATH=~/.simulation-gazebo/models`, so `model://` includes resolve to the *downloaded model store*, silently ignoring copies in this repo or the PX4 tree (this is why earlier SDF edits "did nothing"). Therefore `model.sdf` includes only `model://x500_base` (geometry + sensors, zero tunables, identical in all copies) and **inlines the four MulticopterMotorModel plugins**. Never revert to `model://x500`.
2. **Oversized propulsion, not a stripped robot.** motorConstant 8.54858e-06 → **2.0e-05** (80 N total) AND base mass 1.5 → 1.0 kg. Total 3.41 kg, T/W ≈ 2.4. Rationale: the real DogCopter (Go2 ≈ 15 kg) will always need oversized propulsion, so simulating bigger motors is the honest model; "lighten only" was rejected.
3. **Airframe ID 4030, not 4002.** Stock `4002_gz_x500_depth` collides; rcS matches `${SYS_AUTOSTART}_*` by glob order, so 4002 boots nondeterministically.
4. **Symlink pattern preserved** (PX4 tree stays unmodified, repo is source of truth, portable for other members' machines). Airframe edits need **no PX4 rebuild** — it's a shell script sourced at boot via the symlinked rootfs.
5. **Wheels + DiffDrive restored in the hybrid model** (they were commented out). Gives level ground stance (was resting tilted on the caster sphere) and enables the drive-and-fly concept with one model.
6. **Go2 deferred (M5).** Quadruped walking in Gazebo Harmonic needs ros2_control + champ-style gait controllers — a multi-week separate effort. The wheeled base is the flight-test proxy; design the M3 arbitration interface so the locomotion backend is swappable.
7. Commit + push after every verified milestone; baseline commit before risky changes (explicit user requirement).

## 4. FILES

All paths relative to `/home/weichien241/ros2_ws/src` unless absolute.

| Path | What it is |
|---|---|
| `flight_robot_pkg/flight_robot_pkg/models/flight_robot/model.sdf` | THE hybrid model (rewritten this session): x500_base include with `<pose>0 0 0.35</pose>` override, 4 inlined motor plugins (motorConstant 2.0e-05), 1.0 kg base (ixx=iyy=0.0833, izz=0.125), wheels + DiffDrive + JointStatePublisher, caster, fixed `robot_to_drone_joint` to `base_link`. |
| `flight_robot_pkg/flight_robot_pkg/models/flight_robot/{modified,my_robot,model_hybrid_recommended}.sdf` | Historical variants, NOT used. Don't base work on them. |
| `flight_robot_pkg/flight_robot_pkg/airframes/4030_gz_flight_robot` | PX4 airframe (was 4002_*, renamed+rewritten): CA_ROTOR geometry ±0.174/±0.174, KM ±0.016, MPC_THR_HOVER 0.55, MPC_TKO_SPEED 1.0, MPC_TILTMAX_AIR 25. |
| `flight_robot_pkg/flight_robot_pkg/launch/link_setup.sh` | Creates 3 symlinks into `~/PX4-Autopilot` (model dir, ROMFS airframe, build-rootfs airframe), removes stale 4002 links, prints launch commands. Uses `ln -sfn`. |
| `flight_robot_pkg/flight_robot_pkg/launch/simulation-gazebo.py` | Standalone Gazebo launcher (downloads PX4 model store to `~/.simulation-gazebo/models`, sets GZ_SIM_RESOURCE_PATH, `--headless` supported). Unmodified. |
| `flight_robot_pkg/DEBUGGING_GUIDE.md` | Rewritten: post-mortem of the 5 bugs, runbook, boot sanity checks, tuning levers (real param names), mass-budget table (keep updated when editing the model). |
| `README.md` | Project overview, quick start, roadmap M1–M5 with checkboxes. |
| `CLAUDE.md` | Condensed commands + architecture constraints for future sessions. |
| `my_robot_description/urdf/*.xacro` | Ground-only onboarding bot (URDF: diff drive, 2D gpu_lidar in `lidar.xacro`). Source for M4's lidar. |
| `my_robot_bringup/config/gazebo_bridge.yaml` | ros_gz bridge config for the ground bot — the **template for M2**. |
| `my_robot_bringup/launch/my_robot_gazebo.launch.py` | Ground-bot launch (robot_state_publisher + ros_gz_sim + spawn). |
| `/home/weichien241/PX4-Autopilot` | PX4 v1.16.0-rc1-293. Contains unrelated local experiments (`4001_gz_test_drone`) — ignore, never commit into it. |
| `/home/weichien241/.claude/plans/background-you-are-federated-leaf.md` | The approved plan from this session (full context + roadmap). |

## 5. NEXT STEPS (priority order)

1. **M2 — ROS 2 bridge for the hybrid** (small): create a bridge yaml in `flight_robot_pkg` modeled on `my_robot_bringup/config/gazebo_bridge.yaml`. Gazebo-side topics (verified live this session): `/model/flight_robot_0/cmd_vel` (gz.msgs.Twist, ROS→GZ) and `/odom` (GZ→ROS); check names with `gz topic -l` since the `_0` suffix comes from spawn instancing. Add a launch file + teleop test. Also add `flight_robot_pkg` data files (models/airframes/launch) to `setup.py` `data_files` so `colcon build` installs them (currently only resource/package.xml are listed). Commit.
2. **M3 — Mode arbitration node** (medium): Python node in `flight_robot_pkg/flight_robot_pkg/`, GROUND/FLIGHT states switched by a ROS service. GROUND: forward `/cmd_vel` to DiffDrive, refuse arming. FLIGHT: zero wheel cmd, PX4 flies. Needs Micro XRCE-DDS agent + `px4_msgs` (`/fmu/out/vehicle_status` for state, `/fmu/in/*` if commanding offboard) — this infra is NOT set up yet; budget time. Demo: drive → take off → land → drive. Commit.
3. **M4 — Lidar + Nav2** (medium): port the `gpu_lidar` sensor block from `my_robot_description/urdf/lidar.xacro` into the hybrid SDF (needs a lidar link + `gz::sim::systems::Sensors` plugin; remember to add its mass to the budget and check T/W), bridge `/scan`, bring up Nav2 with a diff-drive controller in GROUND mode. Commit.
4. **M5 — Go2 base** (large, deferred): see Key Decision 6.

## 6. GOTCHAS (hard-won; do not repeat)

- **`PX4_GZ_MODELS` is mandatory** in standalone mode: `PX4_GZ_MODELS=$HOME/PX4-Autopilot/Tools/simulation/gz/models`. Standalone doesn't source `gz_env.sh`; without it the spawn URI is `file:///flight_robot/model.sdf`, gz_bridge fails, and PX4 boots half-dead (the old "won't respond to GCS" symptom).
- **Stale params survive** in `~/PX4-Autopilot/build/px4_sitl_default/rootfs/parameters*.bson`. After any airframe param change: `rm` those files, or old values (e.g. MPC_THR_HOVER 0.9) silently persist.
- **Headless arming block**: with no GCS connected, preflight fails on datalink. Fix per-run with `param set NAV_DLL_ACT 0` (runtime only — deliberately NOT in the airframe file).
- **`ln -sf` onto an existing directory symlink creates a link INSIDE it** (that's where the old recursive `models/flight_robot/flight_robot` self-link came from). Always `ln -sfn`. The self-link is deleted; don't let it come back.
- **Joint `<pose>` places the joint frame, not the child link.** The old model "mounted the drone at 0.35 m" via joint pose — the drone actually sat at x500's own 0.24 m model pose, rotors flush with the box top. Drone height is set by the `<pose>` inside the `<include>`.
- **SDF is FLU, PX4 CA params are FRD**: y sign flips when copying rotor positions from SDF to `CA_ROTORn_PY`. `CA_ROTORn_KM` magnitude must equal the SDF `momentConstant` (currently 0.016); change both together (e.g. to 0.025 if yaw is sluggish — large Izz from the wide base).
- **Visual prop speed is meaningless** (`rotorVelocitySlowdownSim=10`); judge thrust via `listener actuator_motors` (hover ≈ 0.55–0.65, symmetric).
- **Validate SDF** with `SDF_PATH=$HOME/.simulation-gazebo/models gz sdf --check <file>` (plain `GZ_SIM_RESOURCE_PATH` isn't read by `gz sdf`). Warnings about `gz_frame_id` are benign.
- Client binaries `px4-commander`, `px4-listener`, `px4-param` (in `~/PX4-Autopilot/build/px4_sitl_default/bin/`) talk to a running instance — handy for scripted tests; `px4-shutdown` stops it. `px4 -d` runs daemonized (no pxh on stdin).
- `sudo` requires a password in this environment — install user-local (like the gh tarball → `~/.local/bin`) instead of apt when possible.
- WSL2: clipboard via `clip.exe`, GUI Gazebo works but headless (`--headless`) is more reliable for automated tests.

### How to run / test (the canonical loop)

```bash
# once per machine or after moving the repo:
bash flight_robot_pkg/flight_robot_pkg/launch/link_setup.sh

# Terminal 1:
python3 flight_robot_pkg/flight_robot_pkg/launch/simulation-gazebo.py --world default --headless

# Terminal 2:
cd ~/PX4-Autopilot && PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4030 PX4_SIM_MODEL=gz_flight_robot \
  PX4_GZ_MODELS=$HOME/PX4-Autopilot/Tools/simulation/gz/models ./build/px4_sitl_default/bin/px4 -d

# Terminal 3 (test):
cd ~/PX4-Autopilot
./build/px4_sitl_default/bin/px4-param set NAV_DLL_ACT 0
./build/px4_sitl_default/bin/px4-commander takeoff
./build/px4_sitl_default/bin/px4-listener vehicle_local_position   # z ≈ -2.5, vx/vy ≈ 0
./build/px4_sitl_default/bin/px4-listener actuator_motors          # 4 × ~0.585
./build/px4_sitl_default/bin/px4-commander land                    # expect "Disarmed by landing"
gz topic -t /model/flight_robot_0/cmd_vel -m gz.msgs.Twist -p 'linear: {x: 0.5}'   # drives
```

Boot sanity: `LOADING CUSTOM AIRFRAME: 4030_gz_flight_robot` banner, `param show SYS_AUTOSTART` → 4030, `CA_ROTOR0_PX` → 0.174, model level on wheels.
