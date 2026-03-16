# Gen2 Engine Control Simulation — Guide

A software simulation of a Gen2 engine control unit supporting **4, 6, and 8 cylinder** configurations. Each run produces **12 scenarios** (4 driving patterns × 3 cylinder counts), generating one CSV and one PNG per scenario.

---

## State Machine Overview

| State | Description |
|---|---|
| `OFF` | Engine not running |
| `DEFAULT_IDLE` | Engine idling; fires **cylinder 1 only** when RPM drops below the idle minimum |
| `MODE1_POWER` | Pedal at position 2; fires **all cylinders** in the engine-specific firing order |
| `MODE2_ECONOMY` | Pedal held steady for 5 s in power mode; maintains a **captured RPM target** using cylinder 1 only |

### State Transitions

```
OFF ──(start_cmd)──► DEFAULT_IDLE ──(pedal=2)──► MODE1_POWER
                          ▲                           │
                          │         (pedal steady 5s) │
                    (brake=True)                      ▼
                    MODE2_ECONOMY ◄────────────────────
```

---

## Cylinder Configurations

| Cylinders | Idle RPM | Firing Sequence (1-indexed) |
|:---------:|:--------:|:---------------------------:|
| 4 | 650 RPM | 1 → 3 → 2 → 4 |
| 6 | 600 RPM | 1 → 5 → 3 → 6 → 2 → 4 |
| 8 | 550 RPM | 1 → 8 → 4 → 3 → 6 → 5 → 7 → 2 |

---

## Scenarios

All four scenarios run for each cylinder count, producing files prefixed with `4cyl_`, `6cyl_`, or `8cyl_`.

### Scenario 1 — Start & Idle Stabilization
> **`{N}cyl_1_start_idle_stabilization`**

| Phase | Duration | Pedal | Brake |
|---|:-:|:-:|:-:|
| Start engine and hold idle | 10 s | 1 | No |

The engine starts from 0 RPM. The starter provides an initial RPM boost; the controller then maintains idle using intermittent single-cylinder pulses with hysteresis. Demonstrates how quickly the engine stabilises at its idle target.

---

### Scenario 2 — Power Mode to Economy Mode
> **`{N}cyl_2_power_to_economy`**

| Phase | Duration | Pedal | Brake |
|---|:-:|:-:|:-:|
| Start and stabilise | 2 s | 1 | No |
| Press pedal (power mode) | 3 s | 2 | No |
| Hold steady → economy transition | 6 s | 2 | No |
| Continue in economy | 5 s | 2 | No |

After the pedal is held at position 2 for **5 continuous seconds**, the controller captures the current filtered RPM as the `standard_rpm_target` and transitions to `MODE2_ECONOMY`. Economy mode maintains that target efficiently using no cooldown between pulses.

---

### Scenario 3 — Economy → Brake → Default Idle
> **`{N}cyl_3_economy_brake_default`**

| Phase | Duration | Pedal | Brake |
|---|:-:|:-:|:-:|
| Start | 2 s | 1 | No |
| Power mode | 3 s | 2 | No |
| Hold steady → economy | 6 s | 2 | No |
| Economy maintenance | 3 s | 2 | No |
| **Brake applied** | 2 s | 2 | **Yes** |
| Return to default idle | 3 s | 1 | No |

Tests the `brake → DEFAULT_IDLE` transition from economy mode. Applying the brake immediately resets the state back to idle, regardless of pedal position.

---

### Scenario 4 — Pedal Jitter (Mode 1)
> **`{N}cyl_4_pedal_jitter_mode1`**

| Phase | Duration | Pedal | Brake |
|---|:-:|:-:|:-:|
| Start | 2 s | 1 | No |
| Press pedal | 2 s | 2 | No |
| Release (jitter) | 1 s | 1 | No |
| Press again | 2 s | 2 | No |
| Release (jitter) | 1.5 s | 1 | No |
| Press again | 3 s | 2 | No |

The pedal is never held steady for a full 5 seconds, so the engine **never transitions to economy mode**. Validates the stability timer reset logic — the 5-second counter resets every time the pedal position changes.

---

## Generated Output Files

Every scenario produces two files written to the **project root directory**. Old files from the previous run are automatically deleted before each new run.

### CSV — `{N}cyl_{scenario_name}.csv`

A timestep-by-timestep log (Δt = 10 ms) with the following columns:

| Column | Description |
|---|---|
| `time` | Simulation time in seconds |
| `state` | Engine state (`OFF`, `DEFAULT_IDLE`, `MODE1_POWER`, `MODE2_ECONOMY`) |
| `pedal_pos` | Pedal position (1 = off, 2 = pressed) |
| `brake` | Brake active (`True` / `False`) |
| `true_rpm` | Physical RPM from the engine model |
| `measured_rpm` | RPM estimated from Hall sensor pulse interval |
| `filtered_rpm` | Low-pass filtered RPM (α = 0.1) used by the controller |
| `cylinder` | Index of the last cylinder fired (0-indexed) |
| `standard_target` | Captured economy RPM target (0 if not yet set) |
| `active_target` | RPM target currently in use by the controller |

### PNG — `{N}cyl_{scenario_name}.png`

A two-panel plot:

- **Top panel — RPM over time**: True RPM, filtered RPM, and the active RPM target.
- **Bottom panel — State over time**: State machine transitions shown as a step plot.

Use the PNG for a quick visual overview; use the CSV for detailed numerical analysis or post-processing.

---

## Running the Simulation

```bash
python gen2_sim.py
```

All 12 scenarios run sequentially. Stale output files are cleaned up automatically before each run.

To change which cylinder counts are simulated, edit `SUPPORTED_CYLINDER_COUNTS` at the top of `main()`:

```python
SUPPORTED_CYLINDER_COUNTS = [4, 6, 8]  # add or remove values here
```
