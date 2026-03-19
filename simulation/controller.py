"""
simulation.controller — Application layer between UI and simulation core.

Manages the EngineSimulator lifecycle, collects events and history,
and exposes a clean API for dashboards and CLI tools.
"""

import csv
import io
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

from simulation.config import Config, State
from simulation.engine import EngineSimulator
from simulation.events import SimEvent, EventCategory
from simulation.scenarios import SCENARIO_PRESETS, ScenarioPreset


@dataclass
class SimState:
    """Snapshot of the current simulation state for UI consumption."""
    time: float
    state: str
    true_rpm: float
    measured_rpm: float
    filtered_rpm: float
    advance_output: float
    current_cylinder: int
    standard_rpm_target: float
    active_target: float
    is_running: bool
    rpm_valid: bool
    compensation_active: bool
    anti_chatter_active: bool


class SimulationController:
    """High-level controller for the engine simulation.

    Provides a clean, stateless-feeling API suitable for Streamlit
    session_state integration.  All state lives inside this object.
    """

    def __init__(self, config: Optional[Config] = None):
        self._config = config or Config()
        self._sim: Optional[EngineSimulator] = None
        self._events: List[SimEvent] = []
        self._is_running: bool = False
        self._step_count: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self, config: Optional[Config] = None) -> SimState:
        """Reset the simulation with the given (or current) config."""
        if config is not None:
            self._config = config
        self._sim = EngineSimulator(self._config)
        self._events = []
        self._is_running = False
        self._step_count = 0
        self._events.append(SimEvent(
            time=0.0,
            category=EventCategory.SYSTEM,
            message="Simulation reset. Ready to start.",
            data={"cylinder_count": self._config.cylinder_count},
        ))
        return self.get_state()

    def start(self):
        """Mark the simulation as running."""
        if self._sim is None:
            self.reset()
        self._is_running = True
        self._events.append(SimEvent(
            time=self._sim.time if self._sim else 0.0,
            category=EventCategory.SYSTEM,
            message="Simulation started.",
        ))

    def pause(self):
        """Pause the simulation."""
        self._is_running = False
        self._events.append(SimEvent(
            time=self._sim.time if self._sim else 0.0,
            category=EventCategory.SYSTEM,
            message="Simulation paused.",
        ))

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def config(self) -> Config:
        return self._config

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------

    def run_step(self, pedal_pos: int = 1, brake: bool = False,
                 start_cmd: bool = True) -> Optional[dict]:
        """Execute a single simulation timestep.

        Returns the log entry dict, or None if no simulator exists.
        """
        if self._sim is None:
            self.reset()

        entry = self._sim.step(pedal_pos, brake, start_cmd)
        self._step_count += 1

        # Drain the engine's event buffer into our collected events
        self._events.extend(self._sim.event_buffer)
        self._sim.event_buffer.clear()

        return entry

    def run_steps(self, n: int, pedal_pos: int = 1, brake: bool = False,
                  start_cmd: bool = True) -> List[dict]:
        """Execute *n* simulation timesteps with the same inputs."""
        results = []
        for _ in range(n):
            entry = self.run_step(pedal_pos, brake, start_cmd)
            if entry:
                results.append(entry)
        return results

    def run_scenario(self, preset: ScenarioPreset,
                     config: Optional[Config] = None) -> List[dict]:
        """Run a complete scenario preset from start to finish.

        Resets the simulation, then runs all input segments.
        Returns the full log history.
        """
        cfg = config or self._config
        self.reset(cfg)
        self._is_running = True

        self._events.append(SimEvent(
            time=0.0,
            category=EventCategory.INFO,
            message=f"Running scenario: {preset.label}",
            data={"scenario": preset.name},
        ))

        for duration, pedal, brake, start in preset.inputs:
            steps = int(duration / cfg.dt)
            self.run_steps(steps, pedal, brake, start)

        self._is_running = False
        return self.get_history()

    def load_scenario(self, name: str) -> Optional[ScenarioPreset]:
        """Look up a scenario preset by name."""
        for preset in SCENARIO_PRESETS:
            if preset.name == name:
                return preset
        return None

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_state(self) -> SimState:
        """Return a snapshot of the current simulation state."""
        if self._sim is None:
            return SimState(
                time=0.0, state="OFF", true_rpm=0.0, measured_rpm=0.0,
                filtered_rpm=0.0, advance_output=0.0, current_cylinder=0,
                standard_rpm_target=0.0, active_target=0.0,
                is_running=False, rpm_valid=True,
                compensation_active=False, anti_chatter_active=False,
            )

        sim = self._sim
        return SimState(
            time=round(sim.time, 4),
            state=sim.state.value,
            true_rpm=round(sim.true_rpm, 2),
            measured_rpm=round(sim.measured_rpm, 2),
            filtered_rpm=round(sim.filtered_rpm, 2),
            advance_output=round(sim.advance_output, 4),
            current_cylinder=sim.current_cylinder,
            standard_rpm_target=round(sim.standard_rpm_target, 2) if sim.standard_rpm_target else 0.0,
            active_target=round(sim.get_active_rpm_target(), 2),
            is_running=self._is_running,
            rpm_valid=0 <= sim.filtered_rpm <= 8000,
            compensation_active=sim.advance_output > 0.01,
            anti_chatter_active=sim.time < sim._mode2_lockout_until,
        )

    def get_events(self) -> List[SimEvent]:
        """Return all events collected so far."""
        return list(self._events)

    def get_history(self) -> List[dict]:
        """Return the full log history."""
        if self._sim is None:
            return []
        return list(self._sim.log)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_csv(self) -> str:
        """Export the simulation log as a CSV string."""
        if not self._sim or not self._sim.log:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self._sim.log[0].keys())
        writer.writeheader()
        writer.writerows(self._sim.log)
        return output.getvalue()

    def export_events_log(self) -> str:
        """Export the events as a formatted text log."""
        lines = [event.formatted() for event in self._events]
        return "\n".join(lines)

    def export_scenario(self) -> str:
        """Export the current config and history as JSON (for scenario saving)."""
        data = {
            "config": {
                "cylinder_count": self._config.cylinder_count,
                "dt": self._config.dt,
                "pedal_steady_seconds": self._config.pedal_steady_seconds,
                "drag": self._config.drag,
                "pulse_gain": self._config.pulse_gain,
                "hysteresis": self._config.hysteresis,
                "cooldown": self._config.cooldown,
                "filter_alpha": self._config.filter_alpha,
                "max_advance_rpm": self._config.max_advance_rpm,
                "mode2_min_dwell_s": self._config.mode2_min_dwell_s,
            },
            "step_count": self._step_count,
            "events": [
                {"time": e.time, "category": e.category.value, "message": e.message}
                for e in self._events
            ],
        }
        return json.dumps(data, indent=2)
