# 🔌 Solenoid Implementation & Usage Guide

This document outlines the solenoid control system integrated into the Gen 2 Engine Control Simulation. Solenoids are electromechanical actuators that allow the ECU to control physical engine parameters like valve timing, fuel vapor purging, and cylinder activation.

---

## 1. Solenoid Types

The simulation includes three primary solenoid types, each with distinct logic and impact on engine behavior:

### A. VVT (Variable Valve Timing) Solenoid
*   **Purpose**: Adjusts the timing of the intake/exhaust valves to optimize high-RPM performance.
*   **Activation Logic**: Automatically opens when the engine is in `MODE1_POWER` and the RPM exceeds **3,500 RPM**.
*   **Physics Impact**: Increases the `pulse_gain` (power per firing event) by **20%**, simulating the improved volumetric efficiency of optimized valve timing.

### B. Cylinder Deactivation Solenoid
*   **Purpose**: Disables specific cylinders (or valves) during low-load cruising to save fuel.
*   **Activation Logic**: Activates exclusively when the engine enters `MODE2_ECONOMY`.
*   **Physics Impact**: Reduces engine `drag` by **15%** (simulating reduced pumping losses), allowing the engine to maintain cruise RPM with less frequent firing.

### C. EVAP Purge Solenoid
*   **Purpose**: Periodically vents fuel vapors from the charcoal canister into the intake manifold.
*   **Activation Logic**: Cycles every **10 seconds** for a duration of **2 seconds** whenever the engine is not `OFF`.
*   **Physics Impact**: No direct impact on RPM physics in the current version (used primarily for emissions/diagnostic simulation).

---

## 2. Technical Integration

### Event System
Solenoid state changes are emitted as structured events in the simulation buffer:
*   **Category**: `SOLENOID`
*   **Data Payload**: Includes the solenoid name and its new state (`OPEN` or `CLOSED`).

### Controller State
The `SimState` object now includes a `solenoids` dictionary:
```python
state.solenoids = {
    "VVT": True,        # Solenoid is Active/Open
    "Deactivation": False,
    "Purge": True
}
```

---

## 3. Usage in Dashboard

The dashboard provides real-time visualization of solenoid activity:

1.  **Status Indicators**: Located in the "Live Engine State" panel. 
    *   **Green Circle**: Solenoid is active/energized.
    *   **Gray Circle**: Solenoid is inactive/de-energized.
2.  **Event Log**: Every time a solenoid toggles, a timestamped entry appears in the event log (e.g., `[15.40s] [SOLENOID] VVT Solenoid activated (RPM > 3500)`).

---

## 4. Troubleshooting & Diagnostics

If a solenoid is not activating as expected:
1.  **Check the Mode**: VVT requires `MODE1_POWER`. Deactivation requires `MODE2_ECONOMY`.
2.  **Verify RPM**: Ensure the engine has reached the required threshold (3,500 RPM for VVT).
3.  **Check Anti-Chatter**: Rapid mode switching might be blocked by the `mode2_min_dwell_s` guard, preventing solenoids from toggling until the dwell time expires.
