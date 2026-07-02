# HANDOFF3 — DogCopter session handoff (2026-07-02, covers sessions 1–2)

Read this together with `CLAUDE.md` (commands + architecture constraints). This file adds history, decisions, and next steps.

## 1. GOAL

DogCopter is a university club project: a robot dog that transforms into a drone to fly over obstacles it can't walk past, then lands and walks again. The current phase is a comprehensive simulation (ROS 2 Humble + Gazebo Harmonic + PX4 SITL standalone + Nav2 later) using a wheeled "onboarding bot" base with an x500 quad on top as a stand-in for the eventual Unitree Go2 + custom drone. Sessions so far delivered: crash-on-takeoff fixed (M1), git/GitHub established, ROS 2 driving (M2), and GROUND/FLIGHT mode arbitration (M3).

## 2. CURRENT STATE

**Milestones 2 and 3 are done and verified (2026-07-02, second session).**
- M2: `flight_robot_bridge.launch.py` bridges cmd_vel/odom/joint_states/tf/clock; teleop_twist_keyboard drives the hybrid from ROS 2 (verified: 0.5 m/s → odom advanced 3 m). This fixed the user's "can't drive with cmd_vel" issue — there was simply no bridge.
- M3: `mode_manager` node + `flight_robot_bringup.launch.py`; drive → fly → drive commanded entirely from ROS 2 via `/dogcopter/set_flight_mode` (verified end-to-end: hover 2.47 m, teleop ignored in FLIGHT, auto-disarm on land, drove again). px4_msgs pinned to 431c15a in the workspace (gitignored). NEXT: **M4 — lidar + Nav2** (see README roadmap).

**Milestone 1 was achieved and verified in the first session** (headless sim):
- Hybrid vehicle takes off, hovers 35 s+ at 2.5 m with <5 cm drift, motor outputs symmetric at ~0.585, `commander land` touches down on wheels, auto-disarms.
- Ground driving works via the DiffDrive plugin (`gz topic` pub to cmd_vel; 0.5 m/s straight-line verified).
- Full **drive → fly → drive** cycle verified twice in one unbroken sim session.

**Git**: repo at `/home/weichien241/ros2_ws/src` (branch `main`). Milestone commits:
```
1156715 Milestone 3: GROUND/FLIGHT mode manager — ROS 2 drive->fly->drive
5450cb2 Milestone 3a: uXRCE-DDS infra — px4_msgs pinned to 431c15a
6651272 Milestone 2: ROS 2 teleop drives hybrid via ros_gz bridge
21542de Add CLAUDE.md with sim commands and PX4 integration constraints
8d75801 Milestone 1: hybrid vehicle hovers, lands, and drives
ebcab79 Fix hybrid flight model: thrust margin, control geometry, airframe ID
fd24b62 Baseline: DogCopter workspace before flight fixes
```

**GitHub**: https://github.com/WeiChien5241/dogcopter (public), `main` tracks `origin/main`, everything pushed. `gh` v2.63.2 at `~/.local/bin/gh`, authenticated as WeiChien5241, and `gh auth setup-git` is done — plain `git push` works.

User decisions already made (do not re-ask): public repo "dogcopter"; gh CLI over SSH-remote; thrust fix = scale motors up AND lighten base ("Both"); next-step scope = M2+M3 together (done), Go2 stays deferred.

## 3. KEY DECISIONS (do not re-litigate)

1. **Self-contained model.sdf.** `simulation-gazebo.py` hardcodes `GZ_SIM_RESOURCE_PATH=~/.simulation-gazebo/models`, so `model://` includes resolve to the *downloaded model store*, silently ignoring copies in this repo or the PX4 tree (this is why earlier SDF edits "did nothing"). Therefore `model.sdf` includes only `model://x500_base` (geometry + sensors, zero tunables, identical in all copies) and **inlines the four MulticopterMotorModel plugins**. Never revert to `model://x500`.
2. **Oversized propulsion, not a stripped robot.** motorConstant 8.54858e-06 → **2.0e-05** (80 N total) AND base mass 1.5 → 1.0 kg. Total 3.41 kg, T/W ≈ 2.4. Rationale: the real DogCopter (Go2 ≈ 15 kg) will always need oversized propulsion, so simulating bigger motors is the honest model; "lighten only" was rejected.
3. **Airframe ID 4030, not 4002.** Stock `4002_gz_x500_depth` collides; rcS matches `${SYS_AUTOSTART}_*` by glob order, so 4002 boots nondeterministically.
4. **Symlink pattern preserved** (PX4 tree stays unmodified, repo is source of truth, portable for other members' machines). Airframe edits need **no PX4 rebuild** — it's a shell script sourced at boot via the symlinked rootfs.
5. **Wheels + DiffDrive restored in the hybrid model** (they were commented out). Gives level ground stance (was resting tilted on the caster sphere) and enables the drive-and-fly concept with one model.
6. **Go2 deferred (M5).** Quadruped walking in Gazebo Harmonic needs ros2_control + champ-style gait controllers — a multi-week separate effort. The wheeled base is the flight-test proxy; design the M3 arbitration interface so the locomotion backend is swappable.
7. Commit + push after every verified milestone; baseline commit before risky changes (explicit user requirement).
8. **px4_msgs pinned to commit `431c15a`** (byte-matches PX4 main@9e90fd193f), cloned into `~/ros2_ws/src/px4_msgs` but gitignored (third-party). Never `git pull` PX4-Autopilot without re-pinning — message hashes break silently. This PX4 versions DDS topics: subscribe `/fmu/out/vehicle_status_v1` (suffixed); `vehicle_command`/`vehicle_land_detected` are unsuffixed.
9. **M3 wheel plumbing**: teleop → `/cmd_vel` → `mode_manager` (forwards only in GROUND) → `/wheel/cmd_vel` → bridge → DiffDrive. The bridge's `wheel_cmd_topic` launch arg defaults to `/cmd_vel` (M2 standalone use) and the bringup overrides it to `/wheel/cmd_vel` (M3). A zero Twist is published on GROUND exit because DiffDrive holds the last command.
10. **Mode service is async**: `/dogcopter/set_flight_mode` (std_srvs/SetBool) responds accepted/rejected immediately; completion is watched on `/dogcopter/mode` (std_msgs/String, 1 Hz). Fly = NAV_TAKEOFF then ARM retried at 1 Hz; FLIGHT declared on nav_state AUTO_LOITER + airborne; GROUND re-entered only when landed AND auto-disarmed (never force-disarm, never re-enable wheels mid-air).

## 4. FILES

All paths relative to `/home/weichien241/ros2_ws/src` unless absolute.

| Path | What it is |
|---|---|
| `flight_robot_pkg/flight_robot_pkg/models/flight_robot/model.sdf` | THE hybrid model (rewritten this session): x500_base include with `<pose>0 0 0.35</pose>` override, 4 inlined motor plugins (motorConstant 2.0e-05), 1.0 kg base (ixx=iyy=0.0833, izz=0.125), wheels + DiffDrive + JointStatePublisher, caster, fixed `robot_to_drone_joint` to `base_link`. |
| `flight_robot_pkg/flight_robot_pkg/models/flight_robot/{modified,my_robot,model_hybrid_recommended}.sdf` | Historical variants, NOT used. Don't base work on them. |
| `flight_robot_pkg/flight_robot_pkg/airframes/4030_gz_flight_robot` | PX4 airframe (was 4002_*, renamed+rewritten): CA_ROTOR geometry ±0.174/±0.174, KM ±0.016, MPC_THR_HOVER 0.55, MPC_TKO_SPEED 1.0, MPC_TILTMAX_AIR 25. |
| `flight_robot_pkg/flight_robot_pkg/launch/link_setup.sh` | Creates 3 symlinks into `~/PX4-Autopilot` (model dir, ROMFS airframe, build-rootfs airframe), removes stale 4002 links, prints launch commands. Uses `ln -sfn`. |
| `flight_robot_pkg/flight_robot_pkg/launch/simulation-gazebo.py` | Standalone Gazebo launcher (downloads PX4 model store to `~/.simulation-gazebo/models`, sets GZ_SIM_RESOURCE_PATH, `--headless` supported). Unmodified. |
| `flight_robot_pkg/flight_robot_pkg/launch/flight_robot_bridge.launch.py` | M2: ros_gz parameter_bridge with `model_name` (default `flight_robot_0`), `world_name`, `wheel_cmd_topic` args; bridges cmd_vel/odom/joint_states/tf/clock with remaps to plain ROS names. |
| `flight_robot_pkg/flight_robot_pkg/launch/flight_robot_bringup.launch.py` | M3: includes the bridge with `wheel_cmd_topic:=/wheel/cmd_vel` + starts `mode_manager`. |
| `flight_robot_pkg/flight_robot_pkg/mode_manager.py` | M3: GROUND/TAKING_OFF/FLIGHT/LANDING state machine; service `/dogcopter/set_flight_mode`, state on `/dogcopter/mode`; PX4 via VehicleCommand/VehicleStatus/VehicleLandDetected with BEST_EFFORT+TRANSIENT_LOCAL QoS. Entry point `mode_manager` in setup.py. |
| `flight_robot_pkg/flight_robot_pkg/config/flight_robot_bridge.yaml` | Static reference bridge config (default names, no remaps) for manual parameter_bridge runs. |
| `~/ros2_ws/src/px4_msgs` | Third-party, gitignored, pinned to `431c15a`. Rebuild with `colcon build --packages-select px4_msgs` (~7 min). |
| `flight_robot_pkg/DEBUGGING_GUIDE.md` | Rewritten: post-mortem of the 5 bugs, runbook, boot sanity checks, tuning levers (real param names), mass-budget table (keep updated when editing the model). |
| `README.md` | Project overview, quick start, roadmap M1–M5 with checkboxes. |
| `CLAUDE.md` | Condensed commands + architecture constraints for future sessions. |
| `my_robot_description/urdf/*.xacro` | Ground-only onboarding bot (URDF: diff drive, 2D gpu_lidar in `lidar.xacro`). Source for M4's lidar. |
| `my_robot_bringup/config/gazebo_bridge.yaml` | ros_gz bridge config for the ground bot — the **template for M2**. |
| `my_robot_bringup/launch/my_robot_gazebo.launch.py` | Ground-bot launch (robot_state_publisher + ros_gz_sim + spawn). |
| `/home/weichien241/PX4-Autopilot` | PX4 v1.16.0-rc1-293. Contains unrelated local experiments (`4001_gz_test_drone`) — ignore, never commit into it. |
| `/home/weichien241/.claude/plans/background-you-are-federated-leaf.md` | The approved plan from this session (full context + roadmap). |

## 5. NEXT STEPS (priority order)

1. **M4 — Lidar + Nav2** (medium, THE next task): port the `gpu_lidar` sensor block from `my_robot_description/urdf/lidar.xacro` into the hybrid SDF (needs a lidar link on the base + the `gz::sim::systems::Sensors` plugin with ogre2; remember to add its mass to the DEBUGGING_GUIDE budget and check T/W stays ≥ 2). Add `/scan` to the bridge (gz.msgs.LaserScan ↔ sensor_msgs/LaserScan, GZ_TO_ROS). Nav2 needs TF odom→base + a frame tree: the hybrid is SDF-only (no URDF/robot_state_publisher), so either add a minimal URDF for TF or rely on the bridged `/model/.../tf` + static transforms — decide when implementing. Then Nav2 bringup (diff-drive controller/DWB) driving `/cmd_vel` through the existing mode_manager passthrough in GROUND mode. Demo: autonomous A→B on the ground. Commit + push.
2. **M4.5 (optional polish)**: obstacle-triggered transformation — when Nav2 can't find a path / costmap blocked ahead, call `/dogcopter/set_flight_mode` to hop over (the original DogCopter behavior). Design only after M4 works.
3. **M5 — Go2 base** (large, deferred): see Key Decision 6 and the Go2 notes below.

**Go2 facts gathered (for the M5 decision, investigated 2026-07-02):** local `~/go2_try_ws` = CHAMP stack on **Gazebo Classic** (gzserver, gazebo_ros2_control, EffortJointInterface — violates this repo's Harmonic-only rule; mine it for CHAMP gait/joint configs only). User's linked repo `khaledgabr77/unitree_go2_ros2` = CHAMP on **Harmonic but ROS 2 Jazzy** (we're on Humble). Options: (a) port khaledgabr77 configs to Humble+Harmonic — hinges on gz_ros2_control Humble↔Harmonic compatibility with CHAMP's effort interfaces; (b) upgrade project to Jazzy — check PX4 uXRCE-DDS + ros_gz status; (c) keep wheeled proxy longer. The M2/M3 interfaces (/cmd_vel in, mode service) are locomotion-agnostic by design, so nothing blocks any option.

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
- **The Harmonic DiffDrive plugin ignores `<command_topic>`** (only `topic`/`odom_topic`/`tf_topic` are recognized); the command topic is always the default `/model/<name>/cmd_vel`. This was why the user's teleop "didn't work" — plus there was no bridge at all before M2.
- **Instance-suffix drift**: PX4 spawns `flight_robot_${px4_instance}` and never despawns old models. Restart Gazebo whenever PX4 restarts, or the bridge (pinned to `flight_robot_0`) goes silently stale while a `flight_robot_1` appears. Recover: `gz topic -l | grep cmd_vel`, then `model_name:=flight_robot_1` launch arg.
- **NAV_DLL_ACT applies even with XRCE-DDS connected** — DDS is not a MAVLink datalink, so headless arming still needs `param set NAV_DLL_ACT 0` (or QGC running). mode_manager logs a hint after 3 failed arm retries.
- **PX4 QoS**: all `/fmu/*` pubs/subs need BEST_EFFORT + TRANSIENT_LOCAL + KEEP_LAST(1) or you get no data.
- `ros2 launch`/`ros2 topic echo` piped through `head` can hang on buffering — run launches in the background and probe with `timeout N ros2 topic echo --once` instead.

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
gz topic -t /model/flight_robot_0/cmd_vel -m gz.msgs.Twist -p 'linear: {x: 0.5}'   # drives (raw gz, no ROS needed)
```

Boot sanity: `LOADING CUSTOM AIRFRAME: 4030_gz_flight_robot` banner, `param show SYS_AUTOSTART` → 4030, `CA_ROTOR0_PX` → 0.174, model level on wheels.

### The full ROS 2 stack (M2+M3, the normal way to run now)

```bash
cd ~/ros2_ws && colcon build --packages-select flight_robot_pkg && source install/setup.bash
# Terminal 0: MicroXRCEAgent udp4 -p 8888
# Terminal 1: Gazebo, Terminal 2: PX4 (as above; set NAV_DLL_ACT 0 if headless)
# Terminal 3:
ros2 launch flight_robot_pkg flight_robot_bringup.launch.py
# Terminal 4:
ros2 run teleop_twist_keyboard teleop_twist_keyboard              # drives in GROUND
ros2 service call /dogcopter/set_flight_mode std_srvs/srv/SetBool "{data: true}"   # fly
ros2 topic echo /dogcopter/mode                                   # GROUND/TAKING_OFF/FLIGHT/LANDING
ros2 service call /dogcopter/set_flight_mode std_srvs/srv/SetBool "{data: false}"  # land -> GROUND
```
Bridge-only (no mode manager, teleop straight to wheels): `ros2 launch flight_robot_pkg flight_robot_bridge.launch.py`.
