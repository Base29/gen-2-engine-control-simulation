# CYLINDER NUMBERING GUIDE

## Understanding Cylinder Numbers

The simulation uses **0-indexed** numbering (like most programming), but real engines use **1-indexed** numbering.

---

## Conversion Table

| Real Engine | Code (CSV) | Description |
|-------------|------------|-------------|
| Cylinder 1 | 0 | First cylinder |
| Cylinder 2 | 1 | Second cylinder |
| Cylinder 3 | 2 | Third cylinder |
| Cylinder 4 | 3 | Fourth cylinder |

---

## Firing Sequences

### At Idle (DEFAULT_IDLE and MODE2_ECONOMY)

**Real Engine**: Cylinder 1 only
**In CSV**: cylinder = 0

Only one cylinder fires to maintain idle efficiently.

---

### In Power Mode (MODE1_POWER)

**Real Engine Sequence**: 1 → 3 → 2 → 4 → 1 → 3 → 2 → 4 ...

**In CSV**: cylinder = 0 → 2 → 1 → 3 → 0 → 2 → 1 → 3 ...

All four cylinders fire in this specific sequence for balanced power delivery.

---

## How to Read the CSV

When you open the CSV file and look at the `cylinder` column:

### Example from Idle:
```
time,  state,         cylinder
0.00,  DEFAULT_IDLE,  0
0.10,  DEFAULT_IDLE,  0
0.20,  DEFAULT_IDLE,  0
0.30,  DEFAULT_IDLE,  0
```
**Meaning**: Only Cylinder 1 (shown as 0) is firing

---

### Example from Power Mode:
```
time,  state,         cylinder
2.00,  MODE1_POWER,   0
2.10,  MODE1_POWER,   2
2.20,  MODE1_POWER,   1
2.30,  MODE1_POWER,   3
2.40,  MODE1_POWER,   0
2.50,  MODE1_POWER,   2
```
**Meaning**: Cylinders firing in sequence 1→3→2→4→1→3... (shown as 0→2→1→3→0→2...)

---

## Why This Sequence?

The firing order 1→3→2→4 is designed for:
- **Balanced vibration**: Opposite cylinders fire alternately
- **Even power delivery**: Smooth torque output
- **Reduced stress**: Distributes load across the engine

---

## Visual Representation

### Idle Mode:
```
Cylinder:  1    2    3    4
Status:   [X]  [ ]  [ ]  [ ]
          FIRE OFF  OFF  OFF
```

### Power Mode (one complete cycle):
```
Step 1:
Cylinder:  1    2    3    4
Status:   [X]  [ ]  [ ]  [ ]

Step 2:
Cylinder:  1    2    3    4
Status:   [ ]  [ ]  [X]  [ ]

Step 3:
Cylinder:  1    2    3    4
Status:   [ ]  [X]  [ ]  [ ]

Step 4:
Cylinder:  1    2    3    4
Status:   [ ]  [ ]  [ ]  [X]

(Then repeats from Step 1)
```

---

## Checking Your Data

### To verify idle operation:
1. Open the CSV file
2. Filter for `state = DEFAULT_IDLE` or `state = MODE2_ECONOMY`
3. Check `cylinder` column
4. Should see only `0` (Cylinder 1)

### To verify power mode:
1. Open the CSV file
2. Filter for `state = MODE1_POWER`
3. Check `cylinder` column
4. Should see pattern: `0, 2, 1, 3, 0, 2, 1, 3...`
5. This represents: Cyl 1, Cyl 3, Cyl 2, Cyl 4, Cyl 1, Cyl 3, Cyl 2, Cyl 4...

---

## Common Mistakes

❌ **Wrong**: Looking for cylinders 1, 2, 3, 4 in the CSV
✓ **Right**: Looking for cylinders 0, 1, 2, 3 in the CSV

❌ **Wrong**: Expecting sequence 0, 1, 2, 3 in power mode
✓ **Right**: Expecting sequence 0, 2, 1, 3 in power mode

❌ **Wrong**: Expecting all cylinders at idle
✓ **Right**: Only cylinder 0 fires at idle

---

## Quick Reference

| Mode | Active Cylinders | CSV Pattern |
|------|------------------|-------------|
| Idle | 1 only | 0, 0, 0, 0... |
| Power | All 4 | 0, 2, 1, 3, 0, 2, 1, 3... |
| Economy | 1 only | 0, 0, 0, 0... |

---

## Why Only One Cylinder at Idle?

**Efficiency!**

At idle, the engine only needs to overcome:
- Internal friction
- Accessory loads (alternator, etc.)
- Maintain minimum RPM

One cylinder firing intermittently is enough and saves fuel compared to firing all four cylinders.

---

## Starter Motor Simulation

When the engine starts (time = 0.00):
- RPM is 0
- Starter motor effect is simulated by initial pulses
- These pulses bring RPM from 0 to idle range
- Once at idle, normal control takes over

In the CSV, you'll see:
- Rapid pulses in the first 1-2 seconds
- All on cylinder 0 (Cylinder 1)
- RPM rising from 0 to ~650

---

**Remember: In the CSV, always subtract 1 from the real cylinder number, or just remember that 0=1, 1=2, 2=3, 3=4!**
