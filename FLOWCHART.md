# ENGINE CONTROL FLOWCHART

> Covers all supported engine variants: **4-cylinder, 6-cylinder, 8-cylinder**

---

## State Machine (shared by all cylinder counts)

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENGINE START                             │
│                                                                  │
│  ┌──────┐                                                        │
│  │ OFF  │  RPM = 0, No cylinders firing                         │
│  └──┬───┘                                                        │
│     │ start_cmd = True  (Starter motor simulation begins)        │
│     ▼                                                            │
│  ┌──────────────┐                                                │
│  │ DEFAULT_IDLE │  Target: idle_min (see table below)           │
│  │              │  Cylinders: 1 (cylinder 0 only)               │
│  │              │  Cooldown: Yes (0.1 s)                        │
│  │              │  Hysteresis: 50 RPM                           │
│  └──┬──────┬────┘                                                │
│     │      │ pedal_pos = 2  (Driver presses accelerator)        │
│     │      ▼                                                     │
│     │   ┌──────────────┐                                         │
│     │   │ MODE1_POWER  │  Firing threshold rises with RPM       │
│     │   │              │  (advance table, see below)            │
│     │   │              │  Cylinders: ALL, in firing sequence    │
│     │   │              │  Cooldown: Yes (0.1 s)                 │
│     │   └──┬───────┬───┘                                         │
│     │      │       │ pedal steady ≥ 5 s                         │
│     │      │       │ AND anti-chatter lockout expired           │
│     │      │       │ → capture filtered_rpm as standard_target  │
│     │      │       ▼                                             │
│     │      │  ┌───────────────┐                                  │
│     │      │  │ MODE2_ECONOMY │  Target: captured standard_rpm  │
│     │      │  │               │  Cylinders: 1 (cylinder 0 only) │
│     │      │  │               │  Cooldown: NO                   │
│     │      │  │               │  Hysteresis: 50 RPM             │
│     │      │  └───────┬───────┘                                  │
│     │      │          │ pedal_pos ≠ 2  OR  brake = True         │
│     │      │          │ (lockout armed for 2 s on exit)         │
│     │      └──────────┘                                          │
│     │ pedal_pos ≠ 2  (Driver releases accelerator)              │
│     └────────────────────────────────────────────────────────►  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Idle RPM Minimum — per cylinder count

| Engine | `default_idle_rpm_min` | Fire threshold (idle − 50) |
|--------|------------------------|---------------------------|
| 4-cyl  | 650 RPM                | 600 RPM                   |
| 6-cyl  | 600 RPM                | 550 RPM                   |
| 8-cyl  | 550 RPM                | 500 RPM                   |

Larger displacement engines idle at a lower RPM target because they produce more torque per combustion event.

---

## Firing Sequences — per cylinder count

### 4-Cylinder  (real order: 1 → 3 → 2 → 4)
```
Index:       0    1    2    3    0    1  …
Code order:  0  → 2  → 1  → 3  → 0  → 2  …
Real (1-idx):1  → 3  → 2  → 4  → 1  → 3  …
```

### 6-Cylinder  (real order: 1 → 5 → 3 → 6 → 2 → 4)
```
Index:       0    1    2    3    4    5    0  …
Code order:  0  → 4  → 2  → 5  → 1  → 3  → 0  …
Real (1-idx):1  → 5  → 3  → 6  → 2  → 4  → 1  …
```

### 8-Cylinder  (real order: 1 → 8 → 4 → 3 → 6 → 5 → 7 → 2)
```
Index:       0    1    2    3    4    5    6    7    0  …
Code order:  0  → 7  → 3  → 2  → 5  → 4  → 6  → 1  → 0  …
Real (1-idx):1  → 8  → 4  → 3  → 6  → 5  → 7  → 2  → 1  …
```

**In DEFAULT_IDLE and MODE2_ECONOMY only cylinder index 0 fires (single-cylinder efficiency), regardless of engine size.**

---

## Mode 1 — RPM Advance Compensation

The Mode 1 firing threshold is not flat — it rises continuously with RPM, mirroring a centrifugal-advance distributor. This applies to **all cylinder counts** equally.

```
advance_output = interpolate(filtered_rpm, AdvanceTable)

firing_threshold = idle_min + advance_output × max_advance_rpm (400 RPM)

AdvanceTable breakpoints:
  RPM    Advance
   600     0 %      ← threshold = idle_min + 0
   900    25 %
  1400    60 %
  2000    85 %
  3000   100 %      ← threshold = idle_min + 400
```

### Per-engine threshold at selected RPM points

| filtered_rpm | advance | 4-cyl threshold | 6-cyl threshold | 8-cyl threshold |
|-------------|---------|-----------------|-----------------|-----------------|
| 650         | 0 %     | 650 RPM         | 600 RPM         | 550 RPM         |
| 900         | 25 %    | 750 RPM         | 700 RPM         | 650 RPM         |
| 1 400       | 60 %    | 890 RPM         | 840 RPM         | 790 RPM         |
| 2 000       | 85 %    | 990 RPM         | 940 RPM         | 890 RPM         |
| 3 000       | 100 %   | 1 050 RPM       | 1 000 RPM       | 950 RPM         |

---

## Decision Tree for Pulse Firing

```
                    ┌─────────────────┐
                    │ Should fire     │
                    │ pulse?          │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ State = OFF?    │
                    └────┬────────┬───┘
                         │ Yes    │ No
                         ▼        │
                    ┌────────┐    │
                    │  NO    │    │
                    └────────┘    │
                                  │
                    ┌─────────────▼──────────┐
                    │ Cooldown check         │
                    │ (skipped in MODE2)     │
                    └────┬───────────────┬───┘
                         │ Too soon      │ OK
                         ▼               │
                    ┌────────┐           │
                    │  NO    │           │
                    └────────┘           │
                                         │
                    ┌────────────────────▼────────────────┐
                    │ Which state?                        │
                    └─┬──────────┬──────────┬────────────┘
                      │          │          │
         ┌────────────▼──┐  ┌───▼────┐  ┌──▼──────────────┐
         │ MODE1_POWER   │  │ IDLE   │  │ MODE2_ECONOMY   │
         └───────┬───────┘  └───┬────┘  └────────┬────────┘
                 │              │                 │
         ┌───────▼───────────┐  │            ┌────▼──────────┐
         │ rpm < idle_min +  │  │            │ rpm <         │
         │ advance × 400?    │  │            │ (target − 50)?│
         └───┬───────────┬───┘  │            └───┬───────┬───┘
             │ Yes       │ No   │                │ Yes   │ No
             ▼           ▼      │                ▼       ▼
           FIRE          NO   FIRE(if<min−50)  FIRE     NO
```

---

## Cylinder Selection Logic

```
                    ┌─────────────────┐
                    │ Fire pulse      │
                    │ (add 50 RPM)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Which state?    │
                    └─┬─────────────┬─┘
                      │             │
         ┌────────────▼──┐     ┌────▼───────────────┐
         │ MODE1_POWER   │     │ DEFAULT_IDLE or     │
         │               │     │ MODE2_ECONOMY       │
         └───────┬───────┘     └────────┬────────────┘
                 │                      │
    ┌────────────▼─────────────┐        │
    │ Use engine firing seq    │        │
    │                          │        │
    │  4-cyl: 0→2→1→3          │        │
    │  6-cyl: 0→4→2→5→1→3      │        │
    │  8-cyl: 0→7→3→2→5→4→6→1  │        │
    │  Advance sequence index  │        │
    └──────────────────────────┘        │
                                        │
                              ┌─────────▼─────────┐
                              │ Always cylinder 0 │
                              │ (Cylinder 1 real) │
                              └───────────────────┘
```

---

## RPM Dynamics — DEFAULT_IDLE

The pattern is identical in shape across all engine sizes; only the target RPM and fire threshold differ.

```
4-cyl (idle_min = 650)          6-cyl (idle_min = 600)          8-cyl (idle_min = 550)

RPM                             RPM                             RPM
 │                               │                               │
700├──╱╲    ╱╲    ╱╲            650├──╱╲    ╱╲    ╱╲            600├──╱╲    ╱╲    ╱╲
 │  ╱  ╲  ╱  ╲  ╱  ╲            │  ╱  ╲  ╱  ╲  ╱  ╲            │  ╱  ╲  ╱  ╲  ╱  ╲
650├─╲──╱──╲──╱──╲──── Target   600├─╲──╱──╲──╱──╲──── Target   550├─╲──╱──╲──╱──╲──── Target
 │  ╲╱    ╲╱    ╲╱              │  ╲╱    ╲╱    ╲╱              │  ╲╱    ╲╱    ╲╱
600├─────────────────  Thresh   550├─────────────────  Thresh   500├─────────────────  Thresh
 └─────────────────► Time        └─────────────────► Time        └─────────────────► Time
```

---

## RPM Dynamics — MODE1_POWER

All cylinders fire in sequence. The advance table raises the threshold as RPM climbs.

```
4-cyl (sequence: 0→2→1→3)       6-cyl (sequence: 0→4→2→5→1→3)  8-cyl (0→7→3→2→5→4→6→1)

RPM                              RPM                             RPM
 │                                │                               │
1050├ ─ ─ ─ ─ ─ ─  Max thresh   1000├ ─ ─ ─ ─ ─ ─  Max thresh   950├ ─ ─ ─ ─ ─ ─  Max thresh
 │       ╱╲╱╲╱╲╱╲╱╲              │      ╱╲╱╲╱╲╱╲╱╲╱╲             │    ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲
 │      ╱                        │     ╱                          │   ╱
 │     ╱  threshold rises        │    ╱  threshold rises         │  ╱  threshold rises
650├──╱─── idle_min              600├──╱─── idle_min             550├─╱─── idle_min
 │  ▲ ▲ ▲ ▲ ▲ ▲ ▲ ▲             │  ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲             │  ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
 │  4 pulses/cycle               │  6 pulses/cycle                │  8 pulses/cycle
 └──────────────────► Time       └──────────────────► Time        └──────────────────► Time

Advance output CSV column: 0.00 at idle → rises to ~0.85–1.00 at high RPM
```

---

## Pedal Steady Timer Logic (same for all cylinder counts)

```
┌─────────────────────────────────────────────────────────┐
│ Pedal Steady Timer (for economy mode entry)            │
└─────────────────────────────────────────────────────────┘

Time:  0s    1s    2s    3s    4s    5s    6s    7s
       │     │     │     │     │     │     │     │
Pedal: 1     2     2     2     2     2     2     2
       │     │     │     │     │     │     │     │
Timer: 0     0     1     2     3     4     5     ✓
       │     │     │     │     │     │     │     │
State: IDLE  PWR   PWR   PWR   PWR   PWR   PWR   ECON
                   ▲                         ▲     ▲
                   Start counting            │     Transition!
                                        5 s reached

Note: Anti-chatter lockout (2 s) must also have expired before
      the transition fires. On a fresh start it is always 0, so
      no effect during normal first entry.


With Jitter:

Time:  0s    1s    2s    3s    4s    5s    6s    7s
       │     │     │     │     │     │     │     │
Pedal: 1     2     2     1     2     2     2     2
       │     │     │     │     │     │     │     │
Timer: 0     0     1    RESET  0     1     2     3
       │     │     │     │     │     │     │     │
State: IDLE  PWR   PWR   IDLE  PWR   PWR   PWR   PWR  ← never reaches ECON
                   ▲     ▲     ▲
                   Start Reset Restart (timer < 5 → no transition)
```

---

## Anti-Chatter Lockout (Mode 2 guard)

A 2-second lockout fires whenever any Mode 1 ↔ Mode 2 transition occurs.

```
Normal entry    (lockout irrelevant on first entry):
  t=0    t=7    t=7.03
  IDLE → PWR  → ECON     ✓ lockout_until = 9.03 s

Brake exit → immediate re-entry blocked:
  t=15   t=15.1        t=17.1+
  ECON → IDLE (brake)  → can re-enter ECON only after lockout expires
         lockout_until = 17.1 s

Timeline:
  15 s  ──────────── brake ──────── 16 s ──── 17 s ──── 17.1+ s
  ECON              IDLE            IDLE       IDLE      may enter ECON again
                  lockout armed ──────────────────► expires here
```

---

## Brake Override Logic

```
Normal Operation:
Time:  0s    5s    10s   15s   20s
       │     │     │     │     │
State: IDLE  PWR   PWR   ECON  ECON
Brake: OFF   OFF   OFF   OFF   OFF
       └─────┴─────┴─────┴─────┘  Normal progression


With Brake:
Time:  0s    5s    10s   15s   15.1s  17s
       │     │     │     │     │      │
State: IDLE  PWR   PWR   ECON  IDLE   IDLE
Brake: OFF   OFF   OFF   OFF   ON     OFF
                                ▲
                           Immediate transition!
                           (Safety override + lockout armed)
```

---

## Complete Scenario Flow — Scenario 2: Power to Economy

*Cylinder counts shown side-by-side to highlight the only difference: firing sequence in Mode 1.*

```
Phase 1 — Idle (0–2 s)
┌──────────────┐
│ DEFAULT_IDLE │  4-cyl: 650 RPM · 6-cyl: 600 RPM · 8-cyl: 550 RPM
└──────────────┘  1 cylinder (cyl 0) fires in all cases

Phase 2 — Acceleration (2–7 s)
┌──────────────┐  4-cyl firing: 0 → 2 → 1 → 3 → 0 → …
│ MODE1_POWER  │  6-cyl firing: 0 → 4 → 2 → 5 → 1 → 3 → 0 → …
└──────────────┘  8-cyl firing: 0 → 7 → 3 → 2 → 5 → 4 → 6 → 1 → 0 → …
                  Advance output rises as RPM climbs
                  Pedal steady timer: 0 → 1 → 2 → 3 → 4 → 5

Phase 3 — Transition (7 s)
┌──────────────┐
│ MODE1_POWER  │  Timer ≥ 5 s AND lockout expired
└──────┬───────┘  filtered_rpm → standard_rpm_target (captured)
       │
       ▼
┌──────────────┐
│MODE2_ECONOMY │  active_target = standard_rpm_target
└──────────────┘  1 cylinder (cyl 0) fires for all engine sizes

Phase 4 — Economy (7–16 s)
┌──────────────┐
│MODE2_ECONOMY │  Maintain captured RPM efficiently
└──────────────┘  Fire only when rpm < (captured_target − 50)
                  No cooldown restriction
```

---

**Use this flowchart alongside the code and CHANGES.md to understand the full control logic for 4, 6, and 8-cylinder engines.**
