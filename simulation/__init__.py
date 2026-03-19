"""
simulation — Gen2 Engine Control Simulation Package

Provides a clean, reusable API for the engine timing simulation,
separated from any UI or I/O concerns.
"""

from simulation.config import (
    AdvanceTable,
    Config,
    State,
    compute_advance_output,
)
from simulation.engine import EngineSimulator
from simulation.events import SimEvent, EventCategory
from simulation.controller import SimulationController
from simulation.scenarios import SCENARIO_PRESETS, ScenarioPreset

__all__ = [
    "AdvanceTable",
    "Config",
    "State",
    "compute_advance_output",
    "EngineSimulator",
    "SimEvent",
    "EventCategory",
    "SimulationController",
    "SCENARIO_PRESETS",
    "ScenarioPreset",
]
