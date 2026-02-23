# DETAILED SCENARIO NOTES

## HOW TO USE THESE NOTES

1. Run the simulation: `python gen2_sim.py`
2. Open the CSV file for the scenario you want to study
3. Read the notes below to understand what's happening
4. Compare the notes to what you see in the data

---

## SCENARIO 1: Start + Idle Stabilization (10 seconds)

### WHAT THIS TESTS
- Engine starting from cold (0 RPM)
- Starter motor simulation
- Idle stabilization at 650 RPM
- Single cylinder operation at idle

### TIMELINE

**0.00 - 0.10 seconds: Engine Start**
- State: OFF → DEFAULT_IDLE
- Starter provides initial RPM boost
- Valves open
- Cylinder 0 (Cylinder 1 in real engine) begins firing

**0.10 - 2.00 seconds: RPM Rise**
- Pulses fire frequently to bring RPM up from 0
- Each pulse adds 50 RPM
- Drag causes RPM to decay between pulses
- Target: 650 RPM

**2.00 - 10.00 seconds: Idle Stabilization**
- RPM oscillates around 650 RPM
- Pulse fires when RPM drops below 600 (650 - 50 hysteresis)
- Only Cylinder 0 fires (1 cylinder at idle)
- Intermittent pulses maintain idle

### WHAT TO LOOK FOR IN THE CSV

**Column: state**
- Should be "DEFAULT_IDLE" after start

**Column: true_rpm**
- Starts at 0
- Rises to ~650
- Oscillates in sawtooth pattern (decay, pulse, decay, pulse)

**Column: filtered_rpm**
- Smooth version of true_rpm
- Used for control decisions
- Should stabilize around 650

**Column: cylinder**
- Should always be 0 (Cylinder 1)
- Only 1 cylinder fires at idle

**Column: active_target**
- Should be 650.0 throughout

### KEY OBSERVATIONS
- **Starter simulation**: Initial pulses bring RPM from 0
- **1 cylinder at idle**: Only cylinder 0 fires
- **Hysteresis control**: Prevents constant firing
- **Sawtooth RPM**: Natural decay and pulse pattern

### EXPECTED BEHAVIOR
✓ RPM rises from 0 to ~650 in first 2 seconds
✓ RPM stabilizes with small oscillations
✓ Only cylinder 0 fires
✓ Pulses are intermittent (not continuous)
✓ Final RPM between 600-700

---

## SCENARIO 2: Power to Economy Mode (16 seconds)

### WHAT THIS TESTS
- Acceleration with pedal position 2
- 4-cylinder power mode with firing sequence
- Steady pedal detection (5 seconds)
- Transition to economy mode
- Standard RPM target capture

### TIMELINE

**0.00 - 2.00 seconds: Initial Idle**
- State: DEFAULT_IDLE
- RPM stabilizes at 650
- 1 cylinder (cylinder 0) firing

**2.00 - 2.01 seconds: Pedal Pressed**
- Pedal position changes from 1 to 2
- State: DEFAULT_IDLE → MODE1_POWER
- Firing sequence changes to 4 cylinders

**2.01 - 5.00 seconds: Acceleration Phase**
- State: MODE1_POWER
- 4 cylinders fire in sequence: 0 → 2 → 1 → 3 (1 → 3 → 2 → 4 in real engine)
- More frequent pulses
- RPM rises rapidly
- Pedal steady timer starts

**5.00 - 7.00 seconds: Steady Detection**
- State: Still MODE1_POWER
- Pedal held steady at position 2
- Steady timer accumulates
- RPM continues to rise

**7.00 - 7.01 seconds: Economy Mode Transition**
- Pedal has been steady for 5 seconds
- Standard RPM target captured from filtered_rpm
- State: MODE1_POWER → MODE2_ECONOMY
- Firing returns to 1 cylinder (cylinder 0)

**7.01 - 16.00 seconds: Economy Maintenance**
- State: MODE2_ECONOMY
- Active target = captured standard_rpm_target
- 1 cylinder firing (cylinder 0)
- Intermittent pulses only
- No cooldown restriction
- Efficient operation

### WHAT TO LOOK FOR IN THE CSV

**Column: state**
- DEFAULT_IDLE (0-2s)
- MODE1_POWER (2-7s)
- MODE2_ECONOMY (7-16s)

**Column: pedal_pos**
- 1 (0-2s)
- 2 (2-16s)

**Column: cylinder**
- 0 only (0-2s) - idle
- 0, 2, 1, 3 cycling (2-7s) - power sequence
- 0 only (7-16s) - economy

**Column: standard_target**
- 0.0 (0-7s) - not set
- Captured value (7-16s) - set at transition

**Column: active_target**
- 650.0 (0-7s) - default idle
- Captured value (7-16s) - standard target

**Column: true_rpm**
- ~650 (0-2s)
- Rising (2-7s)
- Stabilized at higher RPM (7-16s)

### KEY OBSERVATIONS
- **4-cylinder power**: Sequence 0→2→1→3 (1→3→2→4 in real numbering)
- **Steady detection**: Requires 5 continuous seconds
- **Target capture**: Happens at exact moment of transition
- **Economy efficiency**: Returns to 1 cylinder
- **No cooldown in economy**: Can fire as needed

### EXPECTED BEHAVIOR
✓ RPM rises when pedal pressed
✓ Cylinder sequence changes to 0,2,1,3 in power mode
✓ After 5 seconds steady: standard_target gets set
✓ State changes to MODE2_ECONOMY
✓ Cylinder returns to 0 only
✓ RPM maintained at captured target

---

## SCENARIO 3: Brake Interrupts Economy (19 seconds)

### WHAT THIS TESTS
- Brake safety override
- Immediate exit from economy mode
- Return to default idle
- State reset behavior

### TIMELINE

**0.00 - 14.00 seconds: Same as Scenario 2**
- Progresses through idle → power → economy
- Standard RPM target captured
- Economy mode active

**14.00 - 14.01 seconds: Brake Applied**
- Brake input changes to True
- State: MODE2_ECONOMY → DEFAULT_IDLE (immediate)
- Active target: standard_target → 650 (default idle)
- Pedal steady timer reset
- Note: standard_target value persists in memory

**14.01 - 16.00 seconds: Braking**
- State: DEFAULT_IDLE
- Brake still pressed
- Pedal position still at 2 (ignored due to brake)
- 1 cylinder firing (cylinder 0)
- Target: 650 RPM

**16.00 - 19.00 seconds: Post-Brake Idle**
- Brake released
- Pedal back to position 1
- State: DEFAULT_IDLE
- Normal idle operation
- Target: 650 RPM

### WHAT TO LOOK FOR IN THE CSV

**Column: brake**
- False (0-14s)
- True (14-16s)
- False (16-19s)

**Column: state**
- MODE2_ECONOMY (before 14s)
- DEFAULT_IDLE (14s onward) - immediate change

**Column: active_target**
- Captured value (before 14s)
- 650.0 (14s onward) - reverts to default

**Column: standard_target**
- Captured value throughout (persists in memory)

**Column: cylinder**
- 0 throughout (1 cylinder in both economy and default idle)

### KEY OBSERVATIONS
- **Immediate override**: Brake takes effect instantly
- **Safety priority**: Brake overrides pedal position
- **Target reversion**: Active target returns to default 650
- **Memory persistence**: Standard target value kept but not used
- **No delay**: State change happens in same timestep as brake

### EXPECTED BEHAVIOR
✓ Brake causes immediate state change
✓ Active target drops to 650
✓ Standard target value persists
✓ Pedal position ignored while braking
✓ Normal idle resumes after brake release

---

## SCENARIO 4: Pedal Jitter Prevents Economy (11.5 seconds)

### WHAT THIS TESTS
- Steady pedal detection robustness
- Timer reset on pedal change
- Prevention of accidental economy mode
- State transitions during unstable input

### TIMELINE

**0.00 - 2.00 seconds: Initial Idle**
- State: DEFAULT_IDLE
- Pedal position: 1
- RPM: ~650

**2.00 - 4.00 seconds: First Power Attempt**
- Pedal position: 2
- State: MODE1_POWER
- Steady timer starts
- Duration: 2 seconds (not enough for economy)

**4.00 - 5.00 seconds: First Jitter**
- Pedal position: 2 → 1
- State: MODE1_POWER → DEFAULT_IDLE
- **Steady timer RESET**

**5.00 - 7.00 seconds: Second Power Attempt**
- Pedal position: 1 → 2
- State: DEFAULT_IDLE → MODE1_POWER
- Steady timer restarts from 0
- Duration: 2 seconds (not enough)

**7.00 - 8.50 seconds: Second Jitter**
- Pedal position: 2 → 1
- State: MODE1_POWER → DEFAULT_IDLE
- **Steady timer RESET again**

**8.50 - 11.50 seconds: Third Power Attempt**
- Pedal position: 1 → 2
- State: DEFAULT_IDLE → MODE1_POWER
- Steady timer restarts from 0
- Duration: 3 seconds (still not enough)
- Simulation ends

### WHAT TO LOOK FOR IN THE CSV

**Column: pedal_pos**
- Changes frequently: 1 → 2 → 1 → 2 → 1 → 2
- Never steady for 5 seconds

**Column: state**
- Alternates: DEFAULT_IDLE ↔ MODE1_POWER
- **NEVER reaches MODE2_ECONOMY**

**Column: standard_target**
- Remains 0.0 throughout (never set)

**Column: cylinder**
- 0 only during DEFAULT_IDLE
- 0,2,1,3 sequence during MODE1_POWER
- Pattern changes with state

**Column: true_rpm**
- Fluctuates with state changes
- Rises in power mode
- Drops in idle mode

### KEY OBSERVATIONS
- **Timer reset**: Any pedal change resets steady timer to 0
- **No economy entry**: Never accumulates 5 continuous seconds
- **Robust detection**: Prevents accidental mode changes
- **State bouncing**: Frequent transitions between idle and power
- **Cylinder pattern changes**: Follows state (1 cyl vs 4 cyl)

### EXPECTED BEHAVIOR
✓ State never reaches MODE2_ECONOMY
✓ Standard target never gets set (stays 0.0)
✓ Pedal changes reset the timer
✓ Cylinder pattern changes with state
✓ RPM fluctuates with mode changes

---

## GENERAL DATA ANALYSIS TIPS

### Finding Pulses
Look for jumps in true_rpm of +50 (pulse_gain)

### Finding State Transitions
Filter the state column for changes

### Counting Cylinder Fires
Count how many times each cylinder number appears

### Measuring Efficiency
- Idle/Economy: Fewer pulses = more efficient
- Power: More pulses = more acceleration

### Verifying Hysteresis
Check that pulses fire when filtered_rpm < (active_target - 50)

### Checking Cooldown
In DEFAULT_IDLE and MODE1_POWER: pulses should be at least 0.1s apart
In MODE2_ECONOMY: no cooldown restriction

### Validating Firing Sequence
In MODE1_POWER: cylinder column should show pattern 0,2,1,3,0,2,1,3...
In DEFAULT_IDLE/MODE2_ECONOMY: cylinder column should show only 0

---

## TROUBLESHOOTING DATA ISSUES

**Issue: RPM doesn't stabilize**
- Check drag and pulse_gain parameters
- Verify hysteresis is working

**Issue: Wrong cylinder firing**
- Check state column
- Verify firing sequence in power mode

**Issue: Economy mode not reached**
- Check pedal_pos column for 5 continuous seconds at position 2
- Verify no state changes during that period

**Issue: Brake doesn't work**
- Check brake column changes to True
- Verify state changes immediately

---

**Use these notes alongside the CSV files to understand exactly what's happening at each moment in the simulation.**
