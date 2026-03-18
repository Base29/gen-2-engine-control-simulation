# CHANGES — RPM Advance Compensation & Mode Switching

> **Date:** 2026-03-18  
> **Files changed:** `gen2_sim.py` (modified) · `test_gen2_sim.py` (new)

---

## Why These Changes Were Made

An audit found four problems in the original simulation:

1. **Mode 1 had no RPM-progressive control output** — the firing threshold was a flat `target + 200.0` magic number, identical at 700 RPM and 1 400 RPM. A real cam/timing advance system raises the threshold continuously as RPM climbs.
2. **Mode 1 → Mode 2 had no anti-chatter protection** — once the 5 s timer elapsed, the mode switch could oscillate if RPM was noisy near the boundary.
3. **RPM values were never validated** — a `NaN` or `±Inf` from the Hall sensor would silently corrupt every firing decision downstream.
4. **Zero tests existed** — no automated way to verify correctness.

A fifth issue was discovered during testing:

5. **Pre-existing bug** — when entering Mode 2 with the pedal still at position 2, the very next step's `elif pedal_pos == 2` branch immediately kicked the engine back to Mode 1. The engine never actually stayed in Mode 2.

---

## What Changed

### `gen2_sim.py`

#### New: `AdvanceTable` dataclass
Holds 5 RPM breakpoints mapping engine speed to an advance fraction (0.0 – 1.0). Mirrors the curve of a centrifugal-advance distributor.

```
RPM    → Advance fraction
 600      0 %
 900     25 %
1 400    60 %
2 000    85 %
3 000   100 %
```

#### New: `compute_advance_output(rpm, table)` — pure function
Linearly interpolates the table for any RPM. Fully testable in isolation with no side-effects.

#### Updated: `Config` — three new named fields (no more magic numbers)

| Field | Default | Purpose |
|---|---|---|
| `max_advance_rpm` | `400.0` | Max RPM headroom at full advance (replaced bare `+ 200.0`) |
| `mode2_min_dwell_s` | `2.0` | Lockout seconds after any Mode 1 ↔ 2 switch |
| `advance_table` | 5-point curve above | Breakpoint lookup |

#### Updated: Mode 1 firing threshold — now RPM-progressive

```
# Before (flat, magic number):
return self.filtered_rpm < target + 200.0

# After (progressive, named constant):
threshold = target + self.advance_output * self.config.max_advance_rpm
return self.filtered_rpm < threshold
```

At ~750 RPM → threshold ≈ 698 RPM.  
At 1 400 RPM → threshold = 890 RPM.  
At 3 000 RPM → threshold = 1 050 RPM (ceiling).

#### Updated: Mode 2 entry — anti-chatter lockout

```python
if self.time >= self._mode2_lockout_until:   # NEW guard
    self.standard_rpm_target = self.filtered_rpm
    self.state = State.MODE2_ECONOMY
    self._mode2_lockout_until = self.time + self.config.mode2_min_dwell_s
```

The lockout also fires when brake exits Mode 2, blocking immediate re-entry.

#### Fixed: Mode 2 cruise-hold bug

```python
# Before: jumping back to Mode 1 while pedal was still at 2
elif pedal_pos == 2:
    self.state = State.MODE1_POWER   # ← fired on EVERY step in Mode 2!

# After: stay in Mode 2 while pedal held; exit only when pedal released
elif pedal_pos != 2:
    self.state = State.DEFAULT_IDLE  # proper cruise-hold semantics
```

#### New: `_validate_rpm(value, name)` helper

Clamps to `[0, 8 000]` and raises `ValueError` on `NaN` / `±Inf`. Called after every Hall measurement and after every filter update.

#### New: `advance_output` column in CSV log

Every row now includes `advance_output` (0.0 – 1.0) so reviewers can inspect the advance curve in the data.

---

### `test_gen2_sim.py` — new file

21 deterministic pytest tests (no noise, fixed `dt`):

| Test class | What it proves |
|---|---|
| `TestComputeAdvanceOutput` | Advance fraction is monotone, clamped, and interpolates correctly |
| `TestValidateRpm` | NaN/Inf raises; negative and sky-high values are clamped |
| `TestMode1FiringThreshold` | Firing threshold is strictly higher at higher RPM |
| `TestMode2Entry` | Mode 2 needs ≥ 5 s steady; jitter resets the timer |
| `TestMode2Lockout` | Rapid re-entry is blocked within the dwell window; allowed after |
| `TestBrakeOverride` | Brake always returns to DEFAULT_IDLE from any mode |
| `TestAdvanceOutputLogging` | Column present; near-zero at idle; rises during Mode 1 climb |

Run with:

```bash
python -m pytest test_gen2_sim.py -v
# Expected: 21 passed
```

---

## Verification Results

```
pytest:  21 passed in 0.35 s  ✅
sim:     All 12 scenarios completed successfully  ✅
```

CSV spot-check — `4cyl_2_power_to_economy.csv`:

| time | state | advance_output | active_target |
|---|---|---|---|
| 0.00 | DEFAULT_IDLE | 0.000 | 650.0 |
| 2.00 | MODE1_POWER | 0.124 | 650.0 |
| 7.02 | MODE2_ECONOMY | 0.125 | 750.0 |

`advance_output` stays near zero at idle, rises into Mode 1 as RPM climbs, and stabilises once Mode 2 captures the target RPM.
