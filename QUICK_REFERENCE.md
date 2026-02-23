# QUICK REFERENCE CARD

## Run the Simulation
```bash
python gen2_sim.py
```

---

## Engine Specifications

| Parameter | Value | Description |
|-----------|-------|-------------|
| Idle RPM | 650 | Target RPM at idle |
| Cylinders | 4 | Total cylinders |
| Idle Cylinders | 1 | Only cylinder 0 fires at idle |
| Power Sequence | 1→3→2→4 | Firing order in power mode |
| Hysteresis | 50 RPM | Buffer before firing pulse |
| Pulse Gain | 50 RPM | RPM increase per pulse |

---

## States

| State | When Active | Cylinders | Cooldown |
|-------|-------------|-----------|----------|
| OFF | Before start | None | N/A |
| DEFAULT_IDLE | After start, pedal=1 | 1 (cyl 0) | Yes (0.1s) |
| MODE1_POWER | Pedal=2 | 4 (sequence) | Yes (0.1s) |
| MODE2_ECONOMY | Pedal steady 5s | 1 (cyl 0) | No |

---

## State Transitions

```
OFF --[start]--> DEFAULT_IDLE
                     |
                     |--[pedal=2]--> MODE1_POWER
                     |                   |
                     |                   |--[steady 5s]--> MODE2_ECONOMY
                     |                   |                      |
                     |<--[pedal≠2]-------+                      |
                     |                                          |
                     |<-----------[brake]------------------------+
```

---

## Output Files

### After running, you'll have:

**Scenario 1** (10 seconds):
- `1_start_idle_stabilization.csv`
- `1_start_idle_stabilization.png`

**Scenario 2** (16 seconds):
- `2_power_to_economy.csv`
- `2_power_to_economy.png`

**Scenario 3** (19 seconds):
- `3_economy_brake_default.csv`
- `3_economy_brake_default.png`

**Scenario 4** (11.5 seconds):
- `4_pedal_jitter_mode1.csv`
- `4_pedal_jitter_mode1.png`

---

## CSV Columns

| Column | What It Shows |
|--------|---------------|
| time | Seconds since start |
| state | Current engine state |
| pedal_pos | 1=idle, 2=power |
| brake | True/False |
| true_rpm | Actual RPM |
| filtered_rpm | Smoothed RPM (used for control) |
| cylinder | Which cylinder fired (0-3) |
| standard_target | Captured economy target |
| active_target | Current RPM target |

---

## Key Behaviors

### Idle (DEFAULT_IDLE)
- Target: 650 RPM
- Fires when RPM < 600 (650 - 50)
- Only cylinder 0
- Intermittent pulses

### Power (MODE1_POWER)
- Target: 650 + 200 = 850 RPM
- Fires when RPM < 850
- All 4 cylinders: 0→2→1→3 (1→3→2→4)
- Frequent pulses

### Economy (MODE2_ECONOMY)
- Target: Captured from filtered RPM
- Fires when RPM < (target - 50)
- Only cylinder 0
- No cooldown restriction
- Most efficient

---

## What to Look For

### In Scenario 1:
✓ RPM rises from 0 to ~650
✓ Only cylinder 0 fires
✓ Sawtooth RPM pattern

### In Scenario 2:
✓ RPM jumps when pedal pressed
✓ Cylinder pattern: 0→2→1→3
✓ State changes to MODE2_ECONOMY after 5s
✓ standard_target gets set

### In Scenario 3:
✓ Brake causes immediate state change
✓ Returns to DEFAULT_IDLE
✓ active_target drops to 650

### In Scenario 4:
✓ Never reaches MODE2_ECONOMY
✓ standard_target stays at 0
✓ State bounces between IDLE and POWER

---

## Common Questions

**Q: Why only cylinder 0 at idle?**
A: Efficiency. One cylinder is enough to maintain idle RPM.

**Q: What's the firing sequence in power mode?**
A: Cylinders 1→3→2→4 (0→2→1→3 in code, 0-indexed)

**Q: Why does economy mode have no cooldown?**
A: To allow responsive control while maintaining efficiency.

**Q: How is standard_rpm_target set?**
A: Captured from filtered_rpm when pedal is steady for 5 seconds.

**Q: What resets the steady timer?**
A: Any change in pedal position.

**Q: Does brake override pedal?**
A: Yes, brake immediately exits economy mode regardless of pedal.

---

## Modifying Parameters

Edit `gen2_sim.py` and find the `Config` class:

```python
@dataclass
class Config:
    default_idle_rpm_min: float = 650.0  # Change idle target
    pulse_gain: float = 50.0             # Change pulse strength
    hysteresis: float = 50.0             # Change firing threshold
    pedal_steady_seconds: float = 5.0    # Change economy delay
```

---

## Need More Help?

- **START_HERE.md** - Step-by-step beginner guide
- **SCENARIO_NOTES.md** - Detailed timeline for each scenario
- **README.md** - Complete technical documentation

---

**Happy simulating!**
