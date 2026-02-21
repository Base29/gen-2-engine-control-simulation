# Gen2 4-Cylinder Engine Control Simulation

A comprehensive simulation of a Gen2 engine control algorithm featuring a state machine with idle, power, and economy modes. The simulation models RPM dynamics, Hall sensor pulse generation, and intelligent pulse scheduling across 4 cylinders.

## Overview

This simulation implements a sophisticated engine control system that:
- Maintains idle RPM with intermittent pulses
- Provides power mode for acceleration
- Transitions to economy mode for fuel efficiency
- Uses Hall sensor feedback for RPM measurement
- Employs round-robin cylinder firing with hysteresis and cooldown

## Requirements

### Python Version
- Python 3.7 or higher

### Dependencies
```bash
pip install matplotlib
```

The simulation uses only standard library modules plus matplotlib for visualization:
- `csv` - for logging data
- `dataclasses` - for configuration
- `enum` - for state machine
- `typing` - for type hints
- `matplotlib` - for plotting results

## Running the Simulation

### Basic Execution
```bash
python gen2_sim.py
```

This will run all 4 scenarios sequentially and generate output files for each.

### Expected Output

For each scenario, the simulation generates:
1. **CSV file** - Complete timestep-by-timestep log
2. **PNG plot** - Visual representation of RPM and state transitions
3. **Console summary** - Key statistics and state durations

## Scenarios Explained

### Scenario 1: Start + Idle Stabilization
**Purpose**: Verify basic engine start and idle maintenance

**Input Sequence**:
- Start command issued
- Pedal position 1 (idle)
- Duration: 10 seconds

**What to Look For**:
- State transitions from OFF → DEFAULT_IDLE
- RPM rises from 0 to stabilize around 800 RPM (default_idle_rpm_min)
- Intermittent pulses fire when RPM drops below (target - hysteresis)
- Filtered RPM smoothly tracks true RPM with low-pass filtering
- Cylinder firing follows round-robin pattern (0→1→2→3→0...)

**Expected Behavior**:
- Initial pulse burst to bring RPM up from zero
- Stabilization with periodic pulses to maintain RPM above 750 (800 - 50 hysteresis)
- True RPM oscillates slightly around target due to drag and discrete pulses
- Filtered RPM provides smooth measurement despite Hall sensor discretization

**Files Generated**:
- `1_start_idle_stabilization.csv`
- `1_start_idle_stabilization.png`

---

### Scenario 2: Power to Economy Mode Transition
**Purpose**: Demonstrate acceleration, steady-state detection, and economy mode

**Input Sequence**:
1. Start and stabilize (2 seconds, pedal=1)
2. Pedal to position 2 (3 seconds) - acceleration phase
3. Hold pedal steady at position 2 (6 seconds) - triggers economy mode after 5 seconds
4. Continue in economy mode (5 seconds)

**What to Look For**:

**Phase 1 - Initial Idle (0-2s)**:
- State: DEFAULT_IDLE
- RPM stabilizes around 800

**Phase 2 - Power Mode (2-5s)**:
- State: DEFAULT_IDLE → MODE1_POWER
- More aggressive pulse firing (target = 800 + 200 = 1000 RPM)
- RPM rises rapidly due to frequent pulses
- Pedal steady timer resets on transition

**Phase 3 - Steady Detection (5-11s)**:
- State: MODE1_POWER (pedal held steady)
- Pedal steady timer accumulates
- At 5 seconds of steady pedal: standard_rpm_target is set from filtered_rpm
- State transitions to MODE2_ECONOMY

**Phase 4 - Economy Maintenance (11-16s)**:
- State: MODE2_ECONOMY
- Active target switches to standard_rpm_target (captured value)
- Intermittent pulses only (hysteresis-based)
- More efficient operation than power mode

**Key Observations**:
- Standard RPM target is captured at the moment of transition (around 5-second mark of steady pedal)
- Economy mode uses this captured value as the new minimum target
- Pulse frequency decreases significantly in economy mode
- RPM maintained with minimal fuel consumption

**Files Generated**:
- `2_power_to_economy.csv`
- `2_power_to_economy.png`

---

### Scenario 3: Brake Interrupts Economy Mode
**Purpose**: Verify brake safety override and state reset

**Input Sequence**:
1. Start and stabilize (2 seconds)
2. Enter power mode (3 seconds, pedal=2)
3. Hold steady to enter economy (6 seconds)
4. Continue in economy (3 seconds)
5. **Apply brake** (2 seconds, pedal still at 2)
6. Release brake, return to idle (3 seconds, pedal=1)

**What to Look For**:

**Phase 1-4 (0-14s)**:
- Similar to Scenario 2
- Economy mode established with standard_rpm_target set

**Phase 5 - Brake Applied (14-16s)**:
- **Immediate state transition**: MODE2_ECONOMY → DEFAULT_IDLE
- Brake overrides pedal position
- Pedal steady timer reset
- Active target reverts to default_idle_rpm_min (800 RPM)
- Note: standard_rpm_target persists in memory but is not active

**Phase 6 - Post-Brake (16-19s)**:
- State: DEFAULT_IDLE
- Normal idle maintenance resumes
- RPM maintained around 800 RPM

**Key Observations**:
- Brake provides immediate safety override
- Economy mode cannot be active while braking
- System returns to safe default idle state
- Standard target persists but is not used until economy mode is re-entered

**Files Generated**:
- `3_economy_brake_default.csv`
- `3_economy_brake_default.png`

---

### Scenario 4: Pedal Jitter Prevents Economy Mode
**Purpose**: Demonstrate steady-state detection robustness

**Input Sequence**:
1. Start (2 seconds, pedal=1)
2. Pedal to 2 (2 seconds)
3. **Jitter**: Pedal back to 1 (1 second)
4. Pedal to 2 again (2 seconds)
5. **Jitter**: Pedal back to 1 (1.5 seconds)
6. Pedal to 2 final (3 seconds)

**What to Look For**:

**Throughout Simulation**:
- State alternates: DEFAULT_IDLE ↔ MODE1_POWER
- **Never reaches MODE2_ECONOMY** because pedal never steady for 5 consecutive seconds
- Each pedal position change resets the steady timer
- RPM fluctuates with state changes

**Timing Analysis**:
- First pedal=2 period: 2 seconds (not enough)
- Interrupted by jitter → timer reset
- Second pedal=2 period: 2 seconds (not enough)
- Interrupted by jitter → timer reset
- Third pedal=2 period: 3 seconds (not enough)
- Total simulation ends before 5-second threshold

**Key Observations**:
- Steady-state detection requires continuous stable input
- Any pedal change resets the timer completely
- This prevents accidental economy mode entry during active driving
- Power mode remains active during unstable pedal input
- More aggressive pulse firing throughout (no economy efficiency)

**Files Generated**:
- `4_pedal_jitter_mode1.csv`
- `4_pedal_jitter_mode1.png`

---

## Understanding the Output

### CSV Log Files

Each CSV contains the following columns:

| Column | Description |
|--------|-------------|
| `time` | Simulation time in seconds |
| `state` | Current state (OFF, DEFAULT_IDLE, MODE1_POWER, MODE2_ECONOMY) |
| `pedal_pos` | Pedal position input (1 or 2) |
| `brake` | Brake input (True/False) |
| `true_rpm` | Actual physical RPM (ground truth) |
| `measured_rpm` | RPM estimated from Hall sensor pulses |
| `filtered_rpm` | Low-pass filtered RPM (used for control decisions) |
| `cylinder` | Current cylinder in round-robin sequence (0-3) |
| `standard_target` | Captured standard RPM target (0 if not set) |
| `active_target` | Currently active RPM target for control |

### Plot Interpretation

Each plot contains two subplots:

**Top Plot - RPM Dynamics**:
- **True RPM** (light line): Actual physical RPM with oscillations
- **Filtered RPM** (bold line): Smoothed measurement used for control
- **Active Target** (red dashed): Current RPM target threshold

**Bottom Plot - State Machine**:
- Step plot showing state transitions over time
- Y-axis labels show state names
- Transitions appear as vertical steps

### Console Summary

The summary includes:
- Total simulation time
- Final state and RPM values
- Standard RPM target (if set)
- Time spent in each state

## Configuration Parameters

The simulation behavior can be customized via the `Config` dataclass:

```python
@dataclass
class Config:
    dt: float = 0.01                      # Timestep (seconds)
    cylinder_count: int = 4               # Number of cylinders
    default_idle_rpm_min: float = 800.0   # Minimum idle RPM
    pedal_steady_seconds: float = 5.0     # Time for steady detection
    drag: float = 0.05                    # RPM decay coefficient
    pulse_gain: float = 50.0              # RPM increase per pulse
    hysteresis: float = 50.0              # RPM below target before firing
    cooldown: float = 0.1                 # Min seconds between pulses
    filter_alpha: float = 0.1             # Low-pass filter coefficient
    noise_enabled: bool = False           # Enable random noise
    noise_seed: int = 42                  # Random seed for reproducibility
```

### Key Parameter Effects

**dt (timestep)**:
- Smaller values = more accurate simulation, slower execution
- Larger values = faster execution, less accurate
- Default 0.01s (10ms) provides good balance

**drag**:
- Higher drag = RPM decays faster, more pulses needed
- Lower drag = RPM sustained longer, fewer pulses
- Affects fuel efficiency simulation

**pulse_gain**:
- Higher gain = larger RPM increase per pulse
- Lower gain = more pulses needed to reach target
- Affects acceleration responsiveness

**hysteresis**:
- Larger hysteresis = RPM drops further before pulse fires
- Smaller hysteresis = tighter RPM control, more frequent pulses
- Trade-off between stability and efficiency

**cooldown**:
- Longer cooldown = minimum time between pulses increases
- Prevents over-firing and simulates physical constraints
- Affects maximum acceleration rate

**filter_alpha**:
- Higher alpha (closer to 1.0) = faster response, more noise
- Lower alpha (closer to 0.0) = smoother output, slower response
- Default 0.1 provides good noise rejection

**pedal_steady_seconds**:
- Time required for pedal to be stable before economy mode
- Prevents accidental economy entry during transient driving
- Default 5.0 seconds balances responsiveness and stability

## Technical Details

### State Machine Logic

```
OFF
 └─> start_cmd=True ──> DEFAULT_IDLE
                          │
                          ├─> pedal_pos=2 ──> MODE1_POWER
                          │                      │
                          │                      ├─> pedal steady 5s ──> MODE2_ECONOMY
                          │                      │                          │
                          │                      └─> pedal_pos≠2 ──────────┤
                          │                                                 │
                          └─────────────────────────────────────────────────┘
                                                brake=True
```

### RPM Physics Model

**Decay (every timestep)**:
```
rpm -= drag × rpm × dt
```

**Pulse Addition (when fired)**:
```
rpm += pulse_gain
```

This creates a sawtooth pattern where RPM decays continuously and jumps up with each pulse.

### Hall Sensor Simulation

**Pulse Interval Calculation**:
```
pulses_per_revolution = cylinder_count
interval = 60 / (rpm × pulses_per_revolution)
```

**RPM Estimation**:
```
measured_rpm = 60 / (hall_interval × pulses_per_revolution)
```

**Low-Pass Filter**:
```
filtered_rpm = α × measured_rpm + (1 - α) × filtered_rpm_previous
```

### Pulse Scheduling Logic

**Cooldown Check**:
```
if (current_time - last_pulse_time) < cooldown:
    do not fire
```

**Hysteresis Check**:
```
if filtered_rpm < (active_target - hysteresis):
    fire pulse
```

**MODE1_POWER Exception**:
```
if state == MODE1_POWER:
    if filtered_rpm < (active_target + 200):
        fire pulse  # More aggressive
```

### Round-Robin Cylinder Selection

Cylinders fire in sequence:
```
Pulse 1: Cylinder 0
Pulse 2: Cylinder 1
Pulse 3: Cylinder 2
Pulse 4: Cylinder 3
Pulse 5: Cylinder 0  (wraps around)
...
```

This ensures even wear and balanced operation.

## Troubleshooting

### Issue: Plots not displaying
**Solution**: Ensure matplotlib is installed:
```bash
pip install matplotlib
```

### Issue: CSV files not created
**Solution**: Check write permissions in the current directory

### Issue: RPM never stabilizes
**Solution**: Check configuration parameters:
- Increase `pulse_gain` if RPM rises too slowly
- Decrease `drag` if RPM decays too quickly
- Adjust `hysteresis` for tighter control

### Issue: Economy mode never activates
**Solution**: Verify pedal is held steady at position 2 for full 5 seconds without interruption

### Issue: Simulation runs slowly
**Solution**: Increase `dt` timestep (e.g., from 0.01 to 0.02), though this reduces accuracy

## Extending the Simulation

### Adding New Scenarios

Create custom scenarios by defining input sequences:

```python
run_scenario(
    "Custom_Scenario_Name",
    config,
    [
        (duration1, pedal_pos, brake, start_cmd),
        (duration2, pedal_pos, brake, start_cmd),
        # ... more phases
    ]
)
```

### Modifying Configuration

Create custom configurations:

```python
custom_config = Config(
    dt=0.02,                    # Faster simulation
    pulse_gain=75.0,            # Stronger pulses
    hysteresis=30.0,            # Tighter control
    pedal_steady_seconds=3.0    # Faster economy entry
)

run_scenario("Custom", custom_config, inputs)
```

### Adding Noise

Enable realistic sensor noise:

```python
config = Config(
    noise_enabled=True,
    noise_seed=42  # For reproducibility
)
```

## Performance Characteristics

### Typical Execution Times
- Scenario 1 (10s): ~0.5s execution
- Scenario 2 (16s): ~0.8s execution
- Scenario 3 (19s): ~1.0s execution
- Scenario 4 (11.5s): ~0.6s execution
- Total: ~3-4 seconds for all scenarios

### Memory Usage
- Minimal: ~10-20 MB per scenario
- Scales linearly with simulation duration

### Output File Sizes
- CSV: ~50-100 KB per scenario
- PNG: ~100-200 KB per scenario

## Validation Checklist

Use this checklist to verify simulation correctness:

- [ ] RPM starts at 0 when engine is OFF
- [ ] RPM rises after start command
- [ ] RPM stabilizes around 800 in DEFAULT_IDLE
- [ ] Pulses fire when RPM drops below (target - hysteresis)
- [ ] Cooldown prevents pulses firing too frequently
- [ ] Cylinders fire in round-robin sequence (0,1,2,3,0...)
- [ ] Pedal position 2 triggers MODE1_POWER
- [ ] MODE1_POWER fires pulses more aggressively
- [ ] Steady pedal for 5s captures standard_rpm_target
- [ ] State transitions to MODE2_ECONOMY after steady period
- [ ] Economy mode uses captured standard target
- [ ] Brake immediately exits economy mode
- [ ] Pedal jitter prevents economy mode entry
- [ ] Filtered RPM smoothly tracks measured RPM
- [ ] True RPM shows sawtooth pattern (decay + pulses)

## References

### State Machine Design
The state machine implements a hierarchical control strategy:
- Safety layer: Brake override
- Efficiency layer: Economy mode with learned target
- Performance layer: Power mode for acceleration
- Base layer: Default idle maintenance

### Control Theory
- **Hysteresis control**: Prevents chattering and reduces pulse frequency
- **Low-pass filtering**: Reduces measurement noise and improves stability
- **Cooldown timing**: Implements rate limiting for physical constraints

### Simulation Methodology
- **Fixed timestep integration**: Ensures deterministic, reproducible results
- **Physics-based modeling**: RPM dynamics follow realistic decay and pulse response
- **Sensor simulation**: Hall effect sensor model with discrete pulse timing

## License

This simulation is provided as-is for educational and development purposes.

## Contact

For questions or issues, please refer to the inline code documentation or modify the simulation parameters to explore different behaviors.
