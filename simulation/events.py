"""
simulation.events — Structured event system for the engine simulation.

Replaces print-based debugging with typed, timestamped events that
can be consumed by any UI layer (Streamlit, CLI, logging framework).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class EventCategory(str, Enum):
    """Categories for simulation events."""
    INFO = "INFO"
    WARNING = "WARNING"
    SWITCH = "SWITCH"
    SYSTEM = "SYSTEM"


@dataclass(frozen=True)
class SimEvent:
    """A single structured simulation event.

    Attributes:
        time: Simulation time (seconds) when the event occurred.
        category: Event category (INFO, WARNING, SWITCH, SYSTEM).
        message: Human-readable description suitable for non-technical display.
        data: Optional structured metadata for programmatic consumption.
    """
    time: float
    category: EventCategory
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

    def formatted(self) -> str:
        """Return a single-line formatted string for log display."""
        return f"[{self.time:8.2f}s] [{self.category.value:7s}] {self.message}"
