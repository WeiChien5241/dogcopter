# DogCopter Flight Debugging Guide

> **Status (July 2026): the takeoff crash is FIXED.** The hybrid vehicle
> takes off, hovers stably, lands on its wheels, and can drive on the
> ground — verified end-to-end (drive → fly → drive). This document
> records what was actually wrong, how to run the sim, and how to tune it.

## What was actually wrong (post-mortem)

The crash was five stacked bugs, not one:

1. **Thrust-to-weight ≈ 0.95 — the vehicle physically could not hover.**
   Total mass was 3.65 kg (1.5 kg base + 0.15 kg caster + 2.0 kg x500)
   against ~34 N of max thrust (4 × motorConstant 8.54858e-06 × 1000²).
   `MPC_THR_HOVER 0.9` in the airframe was a symptom of this, not a fix.
   Takeoff saturated all four motors; with zero margin left for attitude
   control, any asymmetry became an uncorrectable tumble ("flies in
   random directions").

2. **Control allocation geometry was wrong.** The airframe declared
   iris-era rotor positions (±0.13 / ±0.22 m, KM 0.05) but the x500's
   rotors are at (±0.174, ±0.174) with momentConstant 0.016. PX4 was
   computing roll/pitch/yaw moments for a different aircraft.

3. **Edits to the x500 SDF were silently ignored.**
   `simulation-gazebo.py` sets `GZ_SIM_RESOURCE_PATH=~/.simulation-gazebo/models`
   for the gz server, so `model://x500` resolved to the *downloaded stock
   copy* — never the copy in this package or in the PX4 tree.

4. **Airframe ID 4002 collided with stock `4002_gz_x500_depth`.** rcS
   matches `${SYS_AUTOSTART}_*` by glob, so which file loaded was luck.
   Also, `PX4_GZ_MODELS` is not set automatically in standalone mode, so
   the spawn URI could be wrong and `gz_bridge` would fail at boot
   (this is why the vehicle sometimes ignored the GCS entirely).

5. **The drone was never actually 0.35 m above the base.** A joint's
   `<pose>` places the joint *frame*, not the child link; the merged
   x500 kept its own z=0.24 model pose, leaving the rotor plane flush
   with the box top. And with the wheels commented out, the model rested
   tilted on the caster sphere alone.

## The fixes (all in this package)

| Fix | Where |
|---|---|
| Include only `model://x500_base` (geometry + sensors, no tunables) with an explicit `<pose>0 0 0.35</pose>` override | `models/flight_robot/model.sdf` |
| Motor plugins inlined, `motorConstant` 2.0e-05 → 80 N total, T/W ≈ 2.4 | `models/flight_robot/model.sdf` |
| Base mass 1.5 → 1.0 kg (total 3.41 kg), inertia rescaled | `models/flight_robot/model.sdf` |
| Wheels + DiffDrive restored (level stance, ground driving) | `models/flight_robot/model.sdf` |
| Rotor geometry ±0.174/±0.174, KM ±0.016 (FLU→FRD: y sign flips vs SDF) | `airframes/4030_gz_flight_robot` |
| Airframe renumbered 4002 → 4030 | `airframes/4030_gz_flight_robot` |
| `MPC_THR_HOVER 0.55`, `MPC_TKO_SPEED 1.0`, `MPC_TILTMAX_AIR 25` | `airframes/4030_gz_flight_robot` |
| `ln -sfn` in the link script (`-f` alone created a recursive self-link) | `launch/link_setup.sh` |

Observed after the fix: hover motor output ≈ 0.585 on all four motors
(symmetric), <5 cm drift over 35 s, clean landing with auto-disarm.

## How to run

```bash
# One-time (and after moving the workspace): create symlinks into PX4
bash flight_robot_pkg/launch/link_setup.sh
# No px4_sitl rebuild needed — the airframe is a shell script sourced at
# boot through the symlinked rootfs. Rebuild only if PX4 source changes.

# Terminal 1 — Gazebo server (+GUI; add --headless on a server)
python3 flight_robot_pkg/launch/simulation-gazebo.py --world default

# Terminal 2 — PX4 SITL standalone
cd ~/PX4-Autopilot
PX4_GZ_STANDALONE=1 PX4_SYS_AUTOSTART=4030 PX4_SIM_MODEL=gz_flight_robot \
PX4_GZ_MODELS=$HOME/PX4-Autopilot/Tools/simulation/gz/models \
./build/px4_sitl_default/bin/px4
```

`PX4_GZ_MODELS` is **required**: standalone mode does not source
`gz_env.sh`, and without it the model spawn URI is broken.

In the pxh shell: `commander takeoff`, `commander land`.
Without QGroundControl connected, arming is blocked by the datalink-loss
check; either start QGC or run `param set NAV_DLL_ACT 0` (runtime only —
don't bake it into the airframe).

Ground driving (Gazebo topic, until the ROS bridge is added):
```bash
gz topic -t /model/flight_robot_0/cmd_vel -m gz.msgs.Twist -p 'linear: {x: 0.5}'
```

## Sanity checks at boot

- The `LOADING CUSTOM AIRFRAME: 4030_gz_flight_robot` banner prints.
- `param show SYS_AUTOSTART` → 4030; `param show CA_ROTOR0_PX` → 0.174.
- No `gz_bridge` errors; model listed as `flight_robot_0` in the log.
- Model rests **level** on two wheels + caster in Gazebo.
- If params look stale after editing the airframe:
  `rm ~/PX4-Autopilot/build/px4_sitl_default/rootfs/parameters*.bson`

## Tuning levers (real PX4 param names)

- **Watch thrust, not the props**: `listener actuator_motors` — hover
  should be ~0.55–0.65 and symmetric. (`rotorVelocitySlowdownSim=10`
  makes the visual prop speed meaningless.)
- **Oscillating**: lower attitude gains first — `MC_ROLL_P` / `MC_PITCH_P`
  6.5 → 5.0.
- **Sluggish attitude**: raise rate gains — `MC_ROLLRATE_P` /
  `MC_PITCHRATE_P` 0.15 → 0.20.
- **Sluggish yaw** (large Izz from the wide base): raise the SDF
  `momentConstant` AND all `CA_ROTORn_KM` **together** (e.g. both to
  0.025) — they must stay equal or allocation is wrong.
- **Simulating a bigger/smaller drone**: scale `motorConstant` in
  `model.sdf` (thrust ∝ motorConstant at a given rotor speed), then
  re-trim `MPC_THR_HOVER` to the observed hover output.
- **Pendulum-like pitching**: reduce the include `<pose>` z (0.35 → 0.30)
  to shrink the CoM-to-rotor-plane lever.

## Mass budget (keep this updated when editing the model)

| Component | Mass | Height (z of CoM) |
|---|---|---|
| Robot base | 1.00 kg | 0.10 m |
| Caster | 0.15 kg | 0.05 m |
| Wheels (2×0.1) | 0.20 kg | 0.10 m |
| x500_base + rotors | 2.06 kg | ~0.35 m |
| **Total** | **3.41 kg** | CoM ≈ 0.22 m |

Max thrust 80 N → T/W ≈ 2.4. If you add payload (lidar, plane mount),
keep T/W ≥ 2.0 or scale `motorConstant` up accordingly.
