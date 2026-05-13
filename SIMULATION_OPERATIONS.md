# 🏎️ Simulation Operations & Data Guide

This guide explains how to run the Gen 2 Engine Control Simulation and how to interpret the data it generates.

---

## 1. How to Run the Simulation

### Prerequisites
Ensure you have the following installed:
*   Python 3.8+
*   Streamlit: `pip install streamlit`
*   Plotly: `pip install plotly`

### Launching the Dashboard
The dashboard is the primary way to interact with the simulation. Run the following command in your terminal from the project root:
```bash
streamlit run dashboard.py
```
This will open the simulation in your default web browser.

---

## 2. Operating the Simulation

### Basic Controls
*   **▶️ Start / ⏸️ Pause**: Toggle the simulation engine.
*   **🔄 Reset**: Clear all history and reset the engine to the `OFF` state.
*   **🟢 Accelerator**: Turn ON to speed up. If held steady for a few seconds, the engine transitions to **Economy Mode**.
*   **🔴 Brake**: Safety override that returns the engine to **Idle Mode** immediately.
*   **⛰️ Engine Load (Terrain)**: Adjust this slider to simulate driving uphill (High Load) or downhill (Low Load).

### Using Scenarios
In the left panel, you can select **Scenario Presets** (e.g., "Rapid Acceleration" or "Boundary Test"). These will automatically run a pre-defined sequence of inputs so you can observe the engine's response without manual clicking.

---

## 3. Checking the Generated Data

The simulation generates data in four primary ways:

### A. Visual Data (Real-time)
1.  **Analog Gauges**: The **Engine RPM** and **Efficiency Score** gauges provide an immediate sense of engine health and fuel economy.
2.  **Visual Engine Block**: Observe the orange flashing cylinders. This shows the actual firing sequence. When **Cylinder Deactivation** is active, you will see the firing frequency decrease.
3.  **Performance Charts**: At the bottom, three charts track **RPM**, **Advance Compensation**, and **Engine Mode** over the entire run.

### B. Technical Data (Metrics)
Expand the **📊 Detailed State** section in the right panel to see precise numerical values for:
*   **True RPM**: The physical engine speed.
*   **Measured RPM**: What the simulated Hall sensor sees.
*   **Total Fuel Consumed**: Total ignition pulses since reset.
*   **Active Target**: The RPM the ECU is currently trying to maintain.

### C. The Event Log
The **📋 Event Log** records every significant change. Look here to see:
*   **Mode Switches**: e.g., `OFF → DEFAULT_IDLE`.
*   **Solenoid Activations**: e.g., `VVT Solenoid activated (RPM > 3500)`.
*   **System Messages**: Simulation start/pause/reset.

### D. Exporting for Deep Analysis
In the **💾 Export Data** section, you can download the raw simulation data:
1.  **Download CSV**: This contains a row for every 10ms of simulation. It is the best way to perform external analysis in Excel or Python.
2.  **Download Event Log**: A text version of the log history.
3.  **Save Scenario (JSON)**: Save the current configuration and results to reload or share later.

---

## 4. Understanding the CSV Columns

If you export a CSV, here is what the columns mean:

| Column | Description |
|---|---|
| `time` | Timestamp in seconds from the start of the simulation. |
| `state` | The active engine mode (OFF, IDLE, POWER, ECONOMY). |
| `pedal_pos` | `1` for released, `2` for pressed. |
| `true_rpm` | The actual speed of the engine crankshaft. |
| `filtered_rpm` | The smoothed RPM value the ECU uses for decision-making. |
| `fuel_consumed` | The cumulative number of fuel pulses fired. |
| `load` | The terrain/load multiplier applied at that moment. |
| `solenoids` | A dictionary string showing which solenoids were `True` (active) or `False`. |
| `cylinder` | The index of the specific cylinder that fired at that timestamp. |

---

## 5. Summary for Laymen
*   **High RPM + High Load** = High Fuel Rate (bad for economy).
*   **Steady Pedal + Low Load** = Economy Mode + Deactivation (best for economy).
*   **Green Indicators** = Solenoids are working to optimize your drive!
