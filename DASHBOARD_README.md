# 🏎️ Engine Timing Simulation Dashboard

## Quick Start

```bash
# Install dependencies
pip install streamlit plotly matplotlib

# Launch the dashboard
streamlit run dashboard.py

# Run original CLI simulation (still works)
python gen2_sim.py

# Run all tests
python -m pytest -v
```

---

## Architecture

```
┌──────────────────────────────────────────────┐
│          UI Layer — dashboard.py             │
│  Streamlit widgets, Plotly charts, exports   │
│  Calls only SimulationController API         │
└───────────────┬──────────────────────────────┘
                │
┌───────────────▼──────────────────────────────┐
│   Application Layer — simulation/controller  │
│   SimulationController: lifecycle, events,   │
│   history, export (CSV/JSON/log)             │
└───────────────┬──────────────────────────────┘
                │
┌───────────────▼──────────────────────────────┐
│   Simulation Core — simulation/engine        │
│   EngineSimulator: state machine, physics,   │
│   Hall sensor, advance, anti-chatter         │
│   Pure logic — zero I/O                      │
└──────────────────────────────────────────────┘
```

---

## File / Module Breakdown

| File | Purpose |
|------|---------|
| `dashboard.py` | Streamlit UI — header, controls, charts, events, export |
| `simulation/__init__.py` | Package init; re-exports public API |
| `simulation/config.py` | `Config`, `AdvanceTable`, `State`, `validate_rpm()`, `compute_advance_output()` |
| `simulation/engine.py` | `EngineSimulator` — core logic with event emission |
| `simulation/events.py` | `SimEvent`, `EventCategory` — structured event system |
| `simulation/scenarios.py` | `ScenarioPreset`, `SCENARIO_PRESETS`, `SCENARIO_INPUTS` |
| `simulation/controller.py` | `SimulationController` — lifecycle, stepping, export |
| `gen2_sim.py` | CLI runner (imports from `simulation/`) |
| `test_gen2_sim.py` | Original 21 tests (unchanged) |
| `test_simulation.py` | New 30 tests for controller/events/presets/export |

---

## Simulation API

```python
from simulation import SimulationController, Config

ctrl = SimulationController(Config(cylinder_count=4))
ctrl.reset()
ctrl.start()

# Step-by-step
entry = ctrl.run_step(pedal_pos=2, brake=False, start_cmd=True)

# Batch steps
results = ctrl.run_steps(500, pedal_pos=1, brake=False, start_cmd=True)

# Run a preset scenario
preset = ctrl.load_scenario("gradual_acceleration")
results = ctrl.run_scenario(preset)

# Query state
state = ctrl.get_state()       # SimState dataclass
events = ctrl.get_events()     # List[SimEvent]
history = ctrl.get_history()   # List[dict]

# Export
csv_str = ctrl.export_csv()
log_str = ctrl.export_events_log()
json_str = ctrl.export_scenario()
```

---

## Dashboard Layout

| Section | Contents |
|---------|----------|
| **Header** | Title, subtitle, 5 metric cards (RPM, Mode, Advance, RPM Status, System State) |
| **Left Panel** | Start/Pause/Reset, accelerator/brake inputs, engine type, speed slider, advanced params (expander), 6 scenario presets |
| **Right Panel** | Large mode badge, 4 status indicators, explanation panel, detailed state (expander) |
| **Charts** | 3 Plotly subplots: RPM vs Time, Advance vs Time, Mode vs Time (step) with mode-switch annotations |
| **Event Log** | Timestamped, categorized (INFO/SWITCH/WARNING/SYSTEM), most recent first |
| **Export** | Download CSV, Download Event Log, Save Scenario JSON |

---

## Scenario Presets

| Preset | Description |
|--------|-------------|
| **Idle** | Cold start → stabilise at idle RPM |
| **Gradual Acceleration** | Idle → smooth power climb → economy mode |
| **Rapid Acceleration** | Aggressive throttle, full advance compensation |
| **High RPM** | Extended high-RPM operation |
| **Unstable RPM** | Erratic pedal — tests anti-chatter protection |
| **Boundary Test** | All transitions: Idle → Power → Economy → Brake → Idle |

---

## Extension Guide

- **Add a new preset**: Add a `ScenarioPreset` to `SCENARIO_PRESETS` in `simulation/scenarios.py`
- **Add a new event type**: Add to `EventCategory` in `simulation/events.py`
- **Change engine parameters**: Modify `Config` defaults in `simulation/config.py`
- **Add a new chart**: Add a trace to the Plotly figure in `dashboard.py`
- **Support new cylinder count**: Add entries to `FIRING_SEQUENCES` and `IDLE_RPM` in `simulation/config.py`

---

## Known Limitations

- Real-time simulation speed is bounded by Streamlit's rerun cycle (~100ms)
- Session state is lost on browser refresh (by design in Streamlit)
- The advance table breakpoints are fixed; a UI editor could be added
- No persistence layer; scenario saves are client-side JSON downloads
