"""
test_simulation.py — Tests for the refactored simulation package.

Covers controller API, event emission, scenario presets, and export
functionality.

Run:
    python -m pytest test_simulation.py -v
"""

import json
import pytest

from simulation import (
    Config,
    State,
    SimulationController,
    SCENARIO_PRESETS,
    EngineSimulator,
)
from simulation.events import EventCategory, SimEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_controller(cylinder_count: int = 4, **overrides) -> SimulationController:
    cfg = Config(cylinder_count=cylinder_count, **overrides)
    ctrl = SimulationController(cfg)
    ctrl.reset()
    return ctrl


# ---------------------------------------------------------------------------
# 1. Controller lifecycle
# ---------------------------------------------------------------------------

class TestControllerLifecycle:
    def test_reset_returns_off_state(self):
        ctrl = _make_controller()
        state = ctrl.get_state()
        assert state.state == "OFF"
        assert state.time == 0.0

    def test_start_marks_running(self):
        ctrl = _make_controller()
        ctrl.start()
        assert ctrl.is_running

    def test_pause_after_start(self):
        ctrl = _make_controller()
        ctrl.start()
        ctrl.pause()
        assert not ctrl.is_running

    def test_reset_clears_history(self):
        ctrl = _make_controller()
        ctrl.run_steps(100, pedal_pos=1, brake=False, start_cmd=True)
        assert len(ctrl.get_history()) == 100
        ctrl.reset()
        assert len(ctrl.get_history()) == 0


# ---------------------------------------------------------------------------
# 2. Stepping
# ---------------------------------------------------------------------------

class TestStepping:
    def test_single_step_returns_log_entry(self):
        ctrl = _make_controller()
        entry = ctrl.run_step(pedal_pos=1, brake=False, start_cmd=True)
        assert "time" in entry
        assert "state" in entry
        assert "filtered_rpm" in entry

    def test_run_steps_returns_n_entries(self):
        ctrl = _make_controller()
        results = ctrl.run_steps(50, pedal_pos=1, brake=False, start_cmd=True)
        assert len(results) == 50

    def test_engine_idles_after_start(self):
        ctrl = _make_controller()
        ctrl.run_steps(500, pedal_pos=1, brake=False, start_cmd=True)
        state = ctrl.get_state()
        assert state.state == "DEFAULT_IDLE"
        assert state.filtered_rpm > 0


# ---------------------------------------------------------------------------
# 3. Event emission
# ---------------------------------------------------------------------------

class TestEventEmission:
    def test_reset_emits_system_event(self):
        ctrl = _make_controller()
        events = ctrl.get_events()
        assert any(e.category == EventCategory.SYSTEM for e in events)

    def test_start_emits_system_event(self):
        ctrl = _make_controller()
        ctrl.start()
        events = ctrl.get_events()
        system_events = [e for e in events if e.category == EventCategory.SYSTEM]
        assert len(system_events) >= 2  # reset + start

    def test_mode_switch_emits_switch_event(self):
        ctrl = _make_controller()
        # Start engine (OFF → DEFAULT_IDLE)
        ctrl.run_steps(200, pedal_pos=1, brake=False, start_cmd=True)
        # Enter power mode (DEFAULT_IDLE → MODE1_POWER)
        ctrl.run_steps(10, pedal_pos=2, brake=False, start_cmd=True)
        events = ctrl.get_events()
        switch_events = [e for e in events if e.category == EventCategory.SWITCH]
        assert len(switch_events) >= 2  # OFF→IDLE, IDLE→POWER

    def test_switch_event_has_human_message(self):
        ctrl = _make_controller()
        ctrl.run_steps(200, pedal_pos=1, brake=False, start_cmd=True)
        events = ctrl.get_events()
        switch_events = [e for e in events if e.category == EventCategory.SWITCH]
        assert len(switch_events) >= 1
        # Should mention "started" or "RPM"
        assert any(("RPM" in e.message or "started" in e.message) for e in switch_events)


# ---------------------------------------------------------------------------
# 4. Scenario presets
# ---------------------------------------------------------------------------

class TestScenarioPresets:
    def test_all_presets_have_metadata(self):
        for preset in SCENARIO_PRESETS:
            assert preset.name
            assert preset.label
            assert preset.description
            assert len(preset.inputs) > 0

    def test_run_scenario_produces_history(self):
        ctrl = _make_controller()
        preset = SCENARIO_PRESETS[0]  # Idle
        results = ctrl.run_scenario(preset)
        assert len(results) > 0

    def test_load_scenario_by_name(self):
        ctrl = _make_controller()
        preset = ctrl.load_scenario("idle")
        assert preset is not None
        assert preset.label == "Idle"

    def test_load_scenario_invalid_name(self):
        ctrl = _make_controller()
        assert ctrl.load_scenario("nonexistent") is None

    @pytest.mark.parametrize("preset", SCENARIO_PRESETS, ids=[p.name for p in SCENARIO_PRESETS])
    def test_preset_runs_without_error(self, preset):
        ctrl = _make_controller()
        results = ctrl.run_scenario(preset)
        assert len(results) > 0
        state = ctrl.get_state()
        assert state.state in ["OFF", "DEFAULT_IDLE", "MODE1_POWER", "MODE2_ECONOMY"]


# ---------------------------------------------------------------------------
# 5. Export functions
# ---------------------------------------------------------------------------

class TestExport:
    def test_export_csv_non_empty(self):
        ctrl = _make_controller()
        ctrl.run_steps(100, pedal_pos=1, brake=False, start_cmd=True)
        csv_data = ctrl.export_csv()
        assert "time" in csv_data
        assert "state" in csv_data
        assert len(csv_data.split("\n")) > 10

    def test_export_events_log(self):
        ctrl = _make_controller()
        ctrl.run_steps(100, pedal_pos=1, brake=False, start_cmd=True)
        log = ctrl.export_events_log()
        assert "SYSTEM" in log or "SWITCH" in log

    def test_export_scenario_json(self):
        ctrl = _make_controller()
        ctrl.run_steps(100, pedal_pos=1, brake=False, start_cmd=True)
        raw = ctrl.export_scenario()
        data = json.loads(raw)
        assert "config" in data
        assert data["config"]["cylinder_count"] == 4
        assert data["step_count"] == 100

    def test_export_csv_empty_when_no_history(self):
        ctrl = _make_controller()
        assert ctrl.export_csv() == ""


# ---------------------------------------------------------------------------
# 6. Multi-cylinder support via controller
# ---------------------------------------------------------------------------

class TestMultiCylinder:
    @pytest.mark.parametrize("cyl", [4, 6, 8])
    def test_controller_with_cylinder_count(self, cyl):
        ctrl = _make_controller(cylinder_count=cyl)
        ctrl.run_steps(500, pedal_pos=1, brake=False, start_cmd=True)
        state = ctrl.get_state()
        assert state.state == "DEFAULT_IDLE"
        assert state.filtered_rpm > 0


# ---------------------------------------------------------------------------
# 7. Engine event buffer
# ---------------------------------------------------------------------------

class TestEngineEventBuffer:
    def test_events_emitted_on_transition(self):
        sim = EngineSimulator(Config())
        # Step with start=True → OFF→DEFAULT_IDLE
        sim.step(1, False, True)
        assert len(sim.event_buffer) >= 1
        assert sim.event_buffer[0].category == EventCategory.SWITCH

    def test_event_buffer_clears(self):
        sim = EngineSimulator(Config())
        sim.step(1, False, True)
        assert len(sim.event_buffer) >= 1
        sim.event_buffer.clear()
        # Next step with no transition → no events
        sim.step(1, False, True)
        assert len(sim.event_buffer) == 0


# ---------------------------------------------------------------------------
# 8. Solenoids
# ---------------------------------------------------------------------------

class TestSolenoids:
    def test_purge_solenoid_cycles(self):
        ctrl = _make_controller()
        # Run for 15 seconds (dt=0.01 -> 1500 steps)
        # Purge is open for first 2s of every 10s cycle
        ctrl.run_steps(10, pedal_pos=1, brake=False, start_cmd=True)
        state = ctrl.get_state()
        assert state.solenoids["Purge"] is True
        
        # Run past 2 seconds
        ctrl.run_steps(200, pedal_pos=1, brake=False, start_cmd=True)
        state = ctrl.get_state()
        assert state.solenoids["Purge"] is False

    def test_vvt_solenoid_at_high_rpm(self):
        ctrl = _make_controller(pulse_gain=200.0, pedal_steady_seconds=10.0, max_advance_rpm=4000.0, dt=0.001) # High gain + small dt
        ctrl.run_steps(100, pedal_pos=1, brake=False, start_cmd=True) # Start engine
        
        # Accelerate
        ctrl.run_steps(100, pedal_pos=2, brake=False, start_cmd=True)
        state = ctrl.get_state()
        # VVT should trigger > 3500 RPM
        if state.filtered_rpm > 3500:
            assert state.solenoids["VVT"] is True
        else:
            # Run more steps (with dt=0.001, we need more steps to cover time)
            ctrl.run_steps(5000, pedal_pos=2, brake=False, start_cmd=True)
            state = ctrl.get_state()
            assert state.filtered_rpm > 3500
            assert state.solenoids["VVT"] is True

    def test_deactivation_solenoid_in_economy(self):
        ctrl = _make_controller(pedal_steady_seconds=1.0)
        ctrl.run_steps(100, pedal_pos=1, brake=False, start_cmd=True) # Start
        
        # Steady pedal for 1.1s
        ctrl.run_steps(10, pedal_pos=2, brake=False, start_cmd=True) # POWER mode
        ctrl.run_steps(110, pedal_pos=2, brake=False, start_cmd=True) # Steady
        
        state = ctrl.get_state()
        assert state.state == "MODE2_ECONOMY"
        assert state.solenoids["Deactivation"] is True

    def test_solenoid_events_emitted(self):
        ctrl = _make_controller()
        # Transitioning to IDLE triggers Purge (if not OFF)
        ctrl.run_steps(10, pedal_pos=1, brake=False, start_cmd=True)
        events = ctrl.get_events()
        assert any(e.category == EventCategory.SOLENOID for e in events)
