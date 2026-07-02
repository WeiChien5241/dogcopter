# Dogcopter Flight & Balance Debugging Guide

## Root Cause Analysis: Why Your Drone Crashes

### The Physics Problem
```
System Mass Distribution (Current):
├─ Robot Platform: 1.5 kg at z = 0.1m (COM)
├─ Caster Wheel:   0.15 kg at z = 0.05m
├─ x500 Drone:     2.0 kg at z = 0.35m (COM)
└─ TOTAL: 3.65 kg

Thrust Vector:      Applied at rotor positions (~z = 0.3-0.4m)
Center of Gravity:  Weighted avg ≈ z = 0.24m (depends on exact geometry)
```

**Why it crashes:**
1. **Margin too small**: x500 motors produce ~1.5x thrust-to-weight ratio
2. **Aerodynamic instability**: A box-shaped robot below creates drag and oscillations
3. **Control moment mismatch**: Motors optimized for x500's CoM, not your hybrid's CoM

---

## Root Cause Diagnosis: 3-Step Process

### Step 1: Does it have thrust?
```bash
# In QGC Manual mode, arm and increase throttle to 20%
# Expected: All 4 motors spin up with similar RPM
# Problem signs:
#   - Only 1-2 motors spin
#   - Motors spin but drone doesn't lift off
#   - Erratic spinning (not smoothly increasing)
```

**If motors don't spin equally → Motor/Airframe Configuration Issue**
**If motors spin but no lift → Insufficient Thrust-to-Weight**

### Step 2: Check attitude stability
```bash
# Hover at 50% throttle (don't release sticks if unstable!)
# Watch QGC attitude indicator
# Expected: Roughly level, small oscillations
# Problem signs:
#   - Continuous pitch/roll oscillation
#   - Oscillations growing larger (diverging)
#   - Oscillations decaying (but crashes anyway) → too heavy
```

**Diverging oscillation → Moment of Inertia / Rate Tuning Issue**
**Decaying oscillation → Mass/Thrust Imbalance Issue**

### Step 3: Monitor sensor data
```bash
# Enable raw IMU telemetry in QGC
# Hover & note:
#   - Is IMU reporting +9.81 m/s² on Z-axis when sitting? (level check)
#   - Do gyro rates match your stick inputs?
#   - Check if accelerometer data is symmetric in X/Y
```

---

## Solutions by Root Cause

### Solution A: If Oscillating (Feedback Control Issue)
**Diagnosis**: Drone oscillates, but oscillations grow over 1-2 seconds, then crashes to side

**Fix in PX4:**
1. Access `Air Velocity Controller > Rate MC PITCH gain (MPC_PITCH_MC)`: **Reduce by 10%**
2. Access `Air Velocity Controller > Rate MC ROLL gain (MPC_ROLL_MC)`: **Reduce by 10%**
3. Test hover again

**Or in SDF** (Physical fix):
- Reduce robot mass by 0.2kg (lighter = less inertia = easier to control)
- Increase drone height offset from 0.35m to 0.40m

### Solution B: If Crashing Immediately (Thrust Issue)
**Diagnosis**: Drone lifts slightly but falls straight down

**Fix in SDF** (Fastest):
```xml
<!-- In model.sdf, increase robot mass reduction: -->
<mass>1.0</mass>  <!-- Reduce from 1.5 to 1.0 kg -->
```

**Or create a lightweight version:**
```xml
<!-- Make the box smaller and lighter -->
<collision name='base_collision'>
  <pose>0 0 0.15 0 0 0</pose>
  <geometry>
    <box>
      <size>0.5 0.35 0.15</size>  <!-- Smaller box -->
    </box>
  </geometry>
</collision>
<mass>0.8</mass>  <!-- Lighter mass -->
```

### Solution C: If Oscillating Asymmetrically (CoM Issue)
**Diagnosis**: Drone tilts to one side during hover

**Fix:**
1. Check if caster wheel offset is exactly at `<pose>0.2 0 0.05...</pose>`
2. Try moving it to center-back: `<pose>0 -0.15 0.05...</pose>`
3. Or shift drone offset:
```xml
<pose relative_to='robot_base_footprint'>0.05 0 0.35 0 0 0</pose>
```
(Small 5cm shift forward can help)

---

## Testing Methodology (SAFE APPROACH)

### Phase 1: Ground Testing (No Flight)
```bash
cd ~/ros2_ws
colcon build
# Test 1: Model loads and sits level
ros2 launch flight_robot_pkg simulation-gazebo.py
# In Gazebo: Check visuals align properly, no weird offset
# In QGC: Arm (don't thrust), check that attitude is level (~0°, ~0° roll/pitch)
```

### Phase 2: Tethered Flight (Hover Only)
```bash
# In QGC: Set mode to STABILIZED or ALTITUDE HOLD
# Increase throttle slowly to 30%
# Drone should lift off ground, hover somewhat stably
# Don't exceed 30% - if unstable, immediate land
```

### Phase 3: Manual Flight (Low Speed)
```bash
# Altitude hold mode with gentle inputs
# Test: Small pitch forward should move forward
# Test: Roll right should move right  
# Don't exceed 1m altitude; keep hands on killswitch
```

### Phase 4: Tuning Flight (Full Testing)
```bash
# Once Phase 3 is stable, increase to 2m altitude
# Begin fine-tuning gains if needed
```

---

## Comparing: x500 vs Iris vs Custom Extraction

| Aspect | x500 (Current) | Iris (if available) | Custom Extracted |
|--------|---|---|---|
| **Mass** | 2.0 kg | ~1.2 kg | Configurable |
| **Thrust** | 15-18 N | 10-12 N | Configurable |
| **PX4 Tuning** | Pre-tuned ✓ | Pre-tuned ✓ | Manual tuning ✗ |
| **Flexibility** | Fixed geometry | Fixed geometry | High ✓ |
| **Development Speed** | Fast | Fast | Slow |
| **For Hybrid** | Good with rebalance | Better (lighter) | Best but hard |

**Recommendation**: Stick with x500 for now. If oscillations persist, try lighter platforms (reduce robot mass).

---

## Comparing: Include Merge vs Custom SDF

### Option 1: Include Merge=True (Your Current)
```xml
<include merge='true'>
  <uri>model://x500</uri>
</include>
```
✓ Simpler
✓ PX4 constants already tuned
✗ Less control over component placement
✗ Harder to visualize/debug

### Option 2: Custom SDF with Extracted Components
```xml
<link name='base_link'>
  <!-- Define fuselage, all props, motors from scratch -->
  <!-- Would need to copy/reference all x500 meshes and definitions -->
</link>
```
✓ Full control
✓ Easier to debug
�3 MUCH more work (copy 500+ lines from x500_base)
✗ Must manually tune all parameters

### Option 3: Hybrid Approach (RECOMMENDED)
```xml
<!-- Keep include for drone, but add external interfaces -->
<include merge='true'>
  <uri>model://x500</uri>
</include>

<!-- Your robot structure in this SDF -->
<link name='robot_base_footprint'>
  <!-- Robot body -->
</link>

<!-- Connect them -->
<joint name='robot_to_drone_joint'>
  <!-- Simple fixed transform -->
</joint>
```

This is what you have now. **This is the right approach.**

---

## PX4 Airframe Configuration

Since you're using a custom model, check if you need a custom PX4 airframe:

```bash
# Your airframe probably uses x500_v2 or similar
# Location: /home/weichien241/PX4-Autopilot/ROMFS/px4fmu_common/init.d-posix/

# If your robot has significantly different CoM, you may need to adjust:
# - COM_OFS_XY_0, COM_OFS_ZYZ_0 (Center of Mass offset)
# - MOT_XX_YY parameters (Motor configuration)
```

For now, **test with the default x500 airframe changes** before creating a custom one.

---

## Quick Test Commands

```bash
# Test 1: Check if model spawns
gz model -m flight_robot --list-properties

# Test 2: Check joint constraints
gz model -m flight_robot -m robot_to_drone_joint --info

# Test 3: Print model structure
gz model -m flight_robot --print-model-tree
```

---

## Summary: What to Do Next

1. **Use the updated model.sdf** with:
   - Robot mass: 1.5 kg
   - Drone offset: 0.35m height
   - Caster wheel: 0.15 kg

2. **Test Phase 1**: Load in Gazebo, check visual alignment

3. **Test Phase 2**: Arm in QGC, check attitude is level

4. **Test Phase 3**: Gentle hover at 30% throttle

5. **If crashes**: Check diagnostics above and try:
   - Reduce robot mass to 1.0 kg
   - Move drone offset to 0.40m
   - Adjust caster wheel position

6. **If oscillates**: Adjust PX4 gains (MPC_PITCH_MC, MPC_ROLL_MC down 10%)

Would you like me to create a specific modified version of your model.sdf with any of these adjustments?
