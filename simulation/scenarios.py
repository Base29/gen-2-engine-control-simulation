"""
simulation.scenarios — Predefined scenario definitions and dashboard presets.

Scenario inputs are cylinder-count-agnostic; the same driving sequences
work for every engine variant.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class ScenarioPreset:
    """A named scenario preset with UI-friendly metadata.

    Attributes:
        name: Machine-readable identifier (e.g. "idle").
        label: Human-readable display name.
        description: Plain-English explanation for non-technical users.
        inputs: List of (duration_s, pedal_pos, brake, start_cmd) segments.
        config_overrides: Optional dict of Config field overrides.
    """
    name: str
    label: str
    description: str
    inputs: List[Tuple[float, int, bool, bool]]
    config_overrides: dict = field(default_factory=dict)


# -----------------------------------------------------------------------
# Original scenario inputs (used by CLI runner for backward compat)
# -----------------------------------------------------------------------

SCENARIO_INPUTS = [
    (
        "1_Start_Idle_Stabilization",
        [
            (10.0, 1, False, True),
        ],
    ),
    (
        "2_Power_To_Economy",
        [
            (2.0, 1, False, True),
            (3.0, 2, False, True),
            (6.0, 2, False, True),
            (5.0, 2, False, True),
        ],
    ),
    (
        "3_Economy_Brake_Default",
        [
            (2.0, 1, False, True),
            (3.0, 2, False, True),
            (6.0, 2, False, True),
            (3.0, 2, False, True),
            (2.0, 2, True, True),
            (3.0, 1, False, True),
        ],
    ),
    (
        "4_Pedal_Jitter_Mode1",
        [
            (2.0, 1, False, True),
            (2.0, 2, False, True),
            (1.0, 1, False, True),
            (2.0, 2, False, True),
            (1.5, 1, False, True),
            (3.0, 2, False, True),
        ],
    ),
]


# -----------------------------------------------------------------------
# Dashboard presets (richer metadata for the UI)
# -----------------------------------------------------------------------

SCENARIO_PRESETS: List[ScenarioPreset] = [
    ScenarioPreset(
        name="idle",
        label="Idle",
        description="Engine starts from cold and stabilises at idle RPM. "
                    "Only one cylinder fires to maintain minimum RPM efficiently.",
        inputs=[
            (10.0, 1, False, True),
        ],
    ),
    ScenarioPreset(
        name="gradual_acceleration",
        label="Gradual Acceleration",
        description="Engine idles briefly, then the driver steadily presses "
                    "the accelerator. RPM climbs smoothly through all cylinders "
                    "firing in sequence, eventually reaching Economy mode.",
        inputs=[
            (2.0, 1, False, True),
            (3.0, 2, False, True),
            (6.0, 2, False, True),
            (5.0, 2, False, True),
        ],
    ),
    ScenarioPreset(
        name="rapid_acceleration",
        label="Rapid Acceleration",
        description="Engine quickly jumps to full power. All cylinders fire "
                    "aggressively. Demonstrates the advance compensation system "
                    "raising the firing threshold as RPM climbs.",
        inputs=[
            (1.0, 1, False, True),
            (8.0, 2, False, True),
            (3.0, 2, False, True),
        ],
    ),
    ScenarioPreset(
        name="high_rpm",
        label="High RPM",
        description="Extended high-RPM operation. Shows advance output reaching "
                    "maximum and the system maintaining stable high-speed control.",
        inputs=[
            (1.0, 1, False, True),
            (12.0, 2, False, True),
            (5.0, 2, False, True),
        ],
    ),
    ScenarioPreset(
        name="unstable_rpm",
        label="Unstable RPM",
        description="Driver repeatedly presses and releases the accelerator. "
                    "Tests anti-chatter protection — the system prevents rapid "
                    "mode switching even under erratic input.",
        inputs=[
            (2.0, 1, False, True),
            (2.0, 2, False, True),
            (1.0, 1, False, True),
            (2.0, 2, False, True),
            (1.5, 1, False, True),
            (3.0, 2, False, True),
        ],
    ),
    ScenarioPreset(
        name="boundary_test",
        label="Boundary Test",
        description="Exercises all state transitions including brake override. "
                    "Engine goes through Idle → Power → Economy → Brake → Idle "
                    "to verify every transition path.",
        inputs=[
            (2.0, 1, False, True),
            (3.0, 2, False, True),
            (6.0, 2, False, True),
            (3.0, 2, False, True),
            (2.0, 2, True, True),
            (3.0, 1, False, True),
        ],
    ),
]
