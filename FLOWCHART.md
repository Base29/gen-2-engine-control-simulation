# ENGINE CONTROL FLOWCHART

## State Machine Visual Guide

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENGINE START                             │
│                                                                  │
│  ┌──────┐                                                        │
│  │ OFF  │  RPM = 0                                              │
│  └──┬───┘  No cylinders firing                                  │
│     │                                                            │
│     │ start_cmd = True                                          │
│     │ (Starter motor simulation begins)                         │
│     ▼                                                            │
│  ┌──────────────┐                                               │
│  │ DEFAULT_IDLE │  Target: 650 RPM                             │
│  │              │  Cylinders: 1 (cylinder 0)                    │
│  │              │  Cooldown: Yes (0.1s)                         │
│  │              │  Hysteresis: 50 RPM                           │
│  └──┬───────┬───┘                                               │
│     │       │                                                    │
│     │       │ pedal_pos = 2                                     │
│     │       │ (Driver presses accelerator)                      │
│     │       ▼                                                    │
│     │    ┌──────────────┐                                       │
│     │    │ MODE1_POWER  │  Target: 650 + 200 = 850 RPM        │
│     │    │              │  Cylinders: 4 (sequence 0→2→1→3)     │
│     │    │              │  Cooldown: Yes (0.1s)                │
│     │    │              │  Hysteresis: Based on history        │
│     │    └──┬───────┬───┘                                       │
│     │       │       │                                            │
│     │       │       │ pedal steady for 5 seconds               │
│     │       │       │ (Capture standard_rpm_target)            │
│     │       │       ▼                                            │
│     │       │    ┌──────────────┐                               │
│     │       │    │MODE2_ECONOMY │  Target: Captured value      │
│     │       │    │              │  Cylinders: 1 (cylinder 0)    │
│     │       │    │              │  Cooldown: NO                 │
│     │       │    │              │  Hysteresis: 50 RPM           │
│     │       │    └──┬───────────┘                               │
│     │       │       │                                            │
│     │       │       │ brake = True                              │
│     │       │       │ (Safety override)                         │
│     │       │       ▼                                            │
│     │       └───────┴─────────────────────────────────────────► │
│     │                                                            │
│     │ pedal_pos ≠ 2                                             │
│     │ (Driver releases accelerator)                             │
│     └────────────────────────────────────────────────────────► │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

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
                    ┌────────┐   │
                    │ NO     │   │
                    │ (Exit) │   │
                    └────────┘   │
                                 │
                    ┌────────────▼────────────┐
                    │ Cooldown check          │
                    │ (Skip if MODE2_ECONOMY) │
                    └────┬────────────────┬───┘
                         │ Too soon       │ OK
                         ▼                │
                    ┌────────┐           │
                    │ NO     │           │
                    │ (Exit) │           │
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
         ┌───────▼───────┐  ┌───▼────────┐  ┌────▼─────────┐
         │ RPM < 850?    │  │ RPM < 600? │  │ RPM < (T-50)?│
         │ (650+200)     │  │ (650-50)   │  │ T=captured   │
         └───┬───────┬───┘  └───┬────┬───┘  └────┬────┬────┘
             │ Yes   │ No       │Yes │No         │Yes │No
             ▼       ▼          ▼    ▼           ▼    ▼
         ┌────┐  ┌────┐     ┌────┐ ┌────┐    ┌────┐ ┌────┐
         │YES │  │ NO │     │YES │ │ NO │    │YES │ │ NO │
         └────┘  └────┘     └────┘ └────┘    └────┘ └────┘
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
                    └─┬──────────────┬┘
                      │              │
         ┌────────────▼──┐      ┌────▼────────────────┐
         │ MODE1_POWER   │      │ DEFAULT_IDLE or     │
         │               │      │ MODE2_ECONOMY       │
         └───────┬───────┘      └────────┬────────────┘
                 │                       │
         ┌───────▼────────────┐         │
         │ Use power sequence │         │
         │ 0 → 2 → 1 → 3      │         │
         │ (1→3→2→4 real)     │         │
         │ Advance index      │         │
         └────────────────────┘         │
                                        │
                              ┌─────────▼─────────┐
                              │ Use cylinder 0    │
                              │ (Cylinder 1 real) │
                              │ Only              │
                              └───────────────────┘
```

---

## RPM Dynamics Over Time

```
DEFAULT_IDLE (1 cylinder):

RPM
 │
700├─────╱╲        ╱╲        ╱╲
 │     ╱  ╲      ╱  ╲      ╱  ╲
650├───╱────╲────╱────╲────╱────╲─── Target
 │  ╱      ╲  ╱      ╲  ╱      ╲
600├─────────╲╱────────╲╱────────╲── Fire threshold
 │           ▲         ▲         ▲
 │         Pulse     Pulse     Pulse
 └─────────────────────────────────► Time
    Sawtooth pattern: decay, pulse, decay, pulse


MODE1_POWER (4 cylinders):

RPM
 │
900├──────────╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲
 │          ╱                  ╲
850├────────╱────────────────────╲─── Target
 │       ╱                        ╲
800├─────╱──────────────────────────╲
 │    ╱                              ╲
750├──╱────────────────────────────────
 │  ▲  ▲  ▲  ▲  ▲  ▲  ▲  ▲  ▲  ▲
 │  Frequent pulses (4 cylinders)
 └─────────────────────────────────► Time
    Rapid rise, frequent pulses


MODE2_ECONOMY (1 cylinder):

RPM
 │
850├─────╱╲           ╱╲           ╱╲
 │     ╱  ╲         ╱  ╲         ╱  ╲
800├───╱────╲───────╱────╲───────╱────╲─── Captured target
 │  ╱      ╲     ╱      ╲     ╱      ╲
750├─────────╲───╱────────╲───╱────────╲── Fire threshold
 │           ▲             ▲             ▲
 │         Pulse         Pulse         Pulse
 └─────────────────────────────────────────► Time
    Wider sawtooth: efficient operation
```

---

## Pedal Steady Timer Logic

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
State: IDLE  POWER POWER POWER POWER POWER POWER ECON
                   ▲                         ▲     ▲
                   │                         │     │
                   Start counting            │     Transition!
                                             │
                                        5 seconds reached


With Jitter:

Time:  0s    1s    2s    3s    4s    5s    6s    7s
       │     │     │     │     │     │     │     │
Pedal: 1     2     2     1     2     2     2     2
       │     │     │     │     │     │     │     │
Timer: 0     0     1     RESET 0     1     2     3
       │     │     │     │     │     │     │     │
State: IDLE  POWER POWER IDLE  POWER POWER POWER POWER
                   ▲     ▲     ▲
                   │     │     │
                   Start │     Restart (never reaches 5)
                         │
                         Reset!
```

---

## Brake Override Logic

```
┌─────────────────────────────────────────────────────────┐
│ Brake Safety Override                                   │
└─────────────────────────────────────────────────────────┘

Normal Operation:
Time:  0s    5s    10s   15s   20s
       │     │     │     │     │
State: IDLE  POWER POWER ECON  ECON
Brake: OFF   OFF   OFF   OFF   OFF
       │     │     │     │     │
       └─────┴─────┴─────┴─────┘  Normal progression


With Brake:
Time:  0s    5s    10s   15s   16s   17s
       │     │     │     │     │     │
State: IDLE  POWER POWER ECON  IDLE  IDLE
Brake: OFF   OFF   OFF   OFF   ON    OFF
       │     │     │     │     │     │
       └─────┴─────┴─────┴─────┘
                               ▲
                               │
                          Immediate transition!
                          (Safety override)
```

---

## Complete Scenario Flow

```
SCENARIO 2: Power to Economy

Phase 1: Idle (0-2s)
┌──────────────┐
│ DEFAULT_IDLE │  650 RPM, 1 cylinder
└──────────────┘

Phase 2: Acceleration (2-7s)
┌──────────────┐
│ MODE1_POWER  │  Rising RPM, 4 cylinders (0→2→1→3)
└──────────────┘  Pedal steady timer: 0→1→2→3→4→5

Phase 3: Transition (7s)
┌──────────────┐
│ MODE1_POWER  │  Timer reaches 5 seconds
└──────┬───────┘  Capture filtered_rpm → standard_rpm_target
       │
       ▼
┌──────────────┐
│MODE2_ECONOMY │  Set active_target = standard_rpm_target
└──────────────┘

Phase 4: Economy (7-16s)
┌──────────────┐
│MODE2_ECONOMY │  Maintain captured RPM, 1 cylinder
└──────────────┘  Efficient operation
```

---

**Use this flowchart alongside the documentation to understand the control logic!**
