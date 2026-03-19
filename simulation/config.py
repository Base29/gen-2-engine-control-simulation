"""
simulation.config — Configuration, constants, and pure helper functions.

Contains all simulation parameters, the state machine enum, advance table,
RPM validation, and pure computation functions.  Zero I/O, zero side-effects.
"""

import math
from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------------------------
# RPM sanity bounds
# ---------------------------------------------------------------------------
MAX_VALID_RPM: float = 8_000.0


def validate_rpm(value: float, name: str) -> float:
    """Return *value* clamped to [0, MAX_VALID_RPM].

    Raises ValueError for NaN / ±Inf so that corrupt Hall measurements
    never silently propagate into firing decisions.
    """
    if not math.isfinite(value):
        raise ValueError(f"{name} is non-finite: {value!r}")
    return max(0.0, min(value, MAX_VALID_RPM))


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class State(Enum):
    OFF = "OFF"
    DEFAULT_IDLE = "DEFAULT_IDLE"
    MODE1_POWER = "MODE1_POWER"
    MODE2_ECONOMY = "MODE2_ECONOMY"


# ---------------------------------------------------------------------------
# Firing sequences & idle RPM per cylinder count
# ---------------------------------------------------------------------------

FIRING_SEQUENCES = {
    4: (0, 2, 1, 3),
    6: (0, 4, 2, 5, 1, 3),
    8: (0, 7, 3, 2, 5, 4, 6, 1),
}

IDLE_RPM = {
    4: 650.0,
    6: 600.0,
    8: 550.0,
}


# ---------------------------------------------------------------------------
# Advance table
# ---------------------------------------------------------------------------

@dataclass
class AdvanceTable:
    """RPM → advance-output lookup table used in MODE1_POWER.

    Each breakpoint is an (rpm, advance_pct) pair where advance_pct is in
    [0.0, 1.0].  Pairs must be sorted by RPM ascending.  Linear interpolation
    is used between breakpoints, clamped at the extremes.
    """
    breakpoints: tuple = (
        (  600, 0.00),
        (  900, 0.25),
        ( 1_400, 0.60),
        ( 2_000, 0.85),
        ( 3_000, 1.00),
    )


def compute_advance_output(rpm: float, table: AdvanceTable) -> float:
    """Linearly interpolate the advance fraction for *rpm* from *table*.

    Returns a value in [0.0, 1.0].  Pure function, no side-effects.
    """
    breakpoints = table.breakpoints
    if rpm <= breakpoints[0][0]:
        return breakpoints[0][1]
    if rpm >= breakpoints[-1][0]:
        return breakpoints[-1][1]

    for i in range(len(breakpoints) - 1):
        rpm_lo, adv_lo = breakpoints[i]
        rpm_hi, adv_hi = breakpoints[i + 1]
        if rpm_lo <= rpm <= rpm_hi:
            t = (rpm - rpm_lo) / (rpm_hi - rpm_lo)
            return adv_lo + t * (adv_hi - adv_lo)

    return breakpoints[-1][1]


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class Config:
    """Simulation configuration with sensible defaults."""
    dt: float = 0.01
    cylinder_count: int = 4
    pedal_steady_seconds: float = 5.0
    drag: float = 0.05
    pulse_gain: float = 50.0
    hysteresis: float = 50.0
    cooldown: float = 0.1
    filter_alpha: float = 0.1
    noise_enabled: bool = False
    noise_seed: int = 42
    max_advance_rpm: float = 400.0
    mode2_min_dwell_s: float = 2.0
    advance_table: AdvanceTable = field(default_factory=AdvanceTable)
    default_idle_rpm_min: float = None          # type: ignore[assignment]
    power_firing_sequence: tuple = None         # type: ignore[assignment]

    def __post_init__(self):
        if self.cylinder_count not in FIRING_SEQUENCES:
            raise ValueError(
                f"Unsupported cylinder_count={self.cylinder_count}. "
                f"Supported values: {sorted(FIRING_SEQUENCES.keys())}"
            )
        if self.default_idle_rpm_min is None:
            self.default_idle_rpm_min = IDLE_RPM[self.cylinder_count]
        if self.power_firing_sequence is None:
            self.power_firing_sequence = FIRING_SEQUENCES[self.cylinder_count]
        if self.max_advance_rpm <= 0:
            raise ValueError("max_advance_rpm must be positive")
        if self.mode2_min_dwell_s < 0:
            raise ValueError("mode2_min_dwell_s must be non-negative")
