"""
simulation.engine — Core engine simulator with structured event emission.

This is the simulation core: pure state-machine logic, RPM physics,
Hall sensor simulation, advance compensation, and anti-chatter lockout.
No I/O (no file writes, no prints, no UI).  Events are emitted to an
internal buffer that the controller layer consumes.
"""

import random
from typing import List, Optional, Dict

from simulation.config import (
    Config,
    State,
    compute_advance_output,
    validate_rpm,
)
from simulation.events import SimEvent, EventCategory


class EngineSimulator:
    """Deterministic engine control simulator.

    Call ``step(pedal_pos, brake, start_cmd)`` to advance by one timestep.
    Read ``event_buffer`` after each step to retrieve structured events.
    """

    def __init__(self, config: Config):
        self.config = config
        self.state = State.OFF
        self.true_rpm: float = 0.0
        self.measured_rpm: float = 0.0
        self.filtered_rpm: float = 0.0
        self.current_cylinder: int = 0
        self.power_sequence_index: int = 0
        self.last_pulse_time: float = -999.0
        self.time: float = 0.0

        # Hall sensor simulation
        self.last_hall_time: float = 0.0
        self.hall_interval: float = 0.0

        # Advance compensation
        self.advance_output: float = 0.0

        # Mode tracking
        self.standard_rpm_target: Optional[float] = None
        self.pedal_steady_start: Optional[float] = None
        self.last_pedal_pos: int = 1
        self._mode2_lockout_until: float = 0.0

        # Log history (list of dicts, one per step)
        self.log: List[dict] = []

        # Structured event buffer — consumed and cleared by the controller
        self.event_buffer: List[SimEvent] = []

        # Solenoid states (name -> active)
        self.solenoids: Dict[str, bool] = {
            "VVT": False,
            "Deactivation": False,
            "Purge": False,
        }
        self._last_purge_toggle: float = 0.0

        # Fuel consumption (cumulative pulses)
        self.fuel_consumed: float = 0.0

        if config.noise_enabled:
            random.seed(config.noise_seed)

    # ------------------------------------------------------------------
    # Event emission helpers
    # ------------------------------------------------------------------

    def _emit(self, category: EventCategory, message: str, **data):
        """Append a structured event to the buffer."""
        self.event_buffer.append(SimEvent(
            time=round(self.time, 4),
            category=category,
            message=message,
            data=data,
        ))

    # ------------------------------------------------------------------
    # Core logic (preserved verbatim from gen2_sim.py)
    # ------------------------------------------------------------------

    def get_active_rpm_target(self) -> float:
        """Return the active RPM target based on state and standard_rpm_target."""
        if self.state == State.MODE2_ECONOMY and self.standard_rpm_target is not None:
            return self.standard_rpm_target
        return self.config.default_idle_rpm_min

    def should_fire_pulse(self) -> bool:
        """Determine if a pulse should be fired based on state and conditions."""
        if self.state == State.OFF:
            return False

        if self.state != State.MODE2_ECONOMY:
            if self.time - self.last_pulse_time < self.config.cooldown:
                return False

        target = self.get_active_rpm_target()

        if self.state == State.MODE1_POWER:
            threshold = target + self.advance_output * self.config.max_advance_rpm
            return self.filtered_rpm < threshold
        elif self.state in (State.DEFAULT_IDLE, State.MODE2_ECONOMY):
            return self.filtered_rpm < (target - self.config.hysteresis)

        return False

    def fire_pulse(self):
        """Fire a pulse on the current cylinder and advance based on mode."""
        gain = self.config.pulse_gain
        if self.solenoids.get("VVT"):
            gain *= 1.2  # 20% power boost from VVT
            
        self.true_rpm += gain
        self.last_pulse_time = self.time
        self.fuel_consumed += 1.0  # Each pulse counts as 1 unit of fuel

        if self.state == State.MODE1_POWER:
            self.current_cylinder = self.config.power_firing_sequence[self.power_sequence_index]
            self.power_sequence_index = (
                (self.power_sequence_index + 1) % len(self.config.power_firing_sequence)
            )
        else:
            self.current_cylinder = 0

    def update_hall_sensor(self):
        """Simulate Hall sensor pulse generation and RPM measurement."""
        if self.true_rpm > 10.0:
            pulses_per_rev = self.config.cylinder_count
            interval = 60.0 / (self.true_rpm * pulses_per_rev)

            if self.time - self.last_hall_time >= interval:
                self.hall_interval = self.time - self.last_hall_time
                self.last_hall_time = self.time

                if self.hall_interval > 0:
                    raw = 60.0 / (self.hall_interval * pulses_per_rev)
                    self.measured_rpm = validate_rpm(raw, "measured_rpm")
        else:
            self.measured_rpm = 0.0

    def update_filtered_rpm(self):
        """Apply low-pass filter to measured RPM, then validate."""
        alpha = self.config.filter_alpha
        raw = alpha * self.measured_rpm + (1 - alpha) * self.filtered_rpm
        self.filtered_rpm = validate_rpm(raw, "filtered_rpm")

    def update_rpm_physics(self, load: float = 1.0):
        """Update true RPM based on drag and load."""
        drag = self.config.drag * load
        if self.solenoids.get("Deactivation"):
            drag *= 0.85  # 15% drag reduction from deactivation
            
        self.true_rpm -= drag * self.true_rpm * self.config.dt
        self.true_rpm = max(0.0, self.true_rpm)

    def update_state(self, pedal_pos: int, brake: bool, start_cmd: bool):
        """Update state machine based on inputs.  Emits events on transitions."""
        # Track pedal stability
        if pedal_pos != self.last_pedal_pos:
            self.pedal_steady_start = None
        elif pedal_pos == 2 and self.pedal_steady_start is None:
            self.pedal_steady_start = self.time
        self.last_pedal_pos = pedal_pos

        prev_state = self.state

        # State transitions
        if self.state == State.OFF:
            if start_cmd:
                self.state = State.DEFAULT_IDLE

        elif self.state == State.DEFAULT_IDLE:
            if pedal_pos == 2:
                self.state = State.MODE1_POWER
                self.pedal_steady_start = None

        elif self.state == State.MODE1_POWER:
            if pedal_pos != 2:
                self.state = State.DEFAULT_IDLE
                self.pedal_steady_start = None
            elif self.pedal_steady_start is not None:
                steady_duration = self.time - self.pedal_steady_start
                if steady_duration >= self.config.pedal_steady_seconds:
                    if self.time >= self._mode2_lockout_until:
                        self.standard_rpm_target = self.filtered_rpm
                        self.state = State.MODE2_ECONOMY
                        self._mode2_lockout_until = (
                            self.time + self.config.mode2_min_dwell_s
                        )

        elif self.state == State.MODE2_ECONOMY:
            if brake:
                self.state = State.DEFAULT_IDLE
                self.pedal_steady_start = None
                self._mode2_lockout_until = (
                    self.time + self.config.mode2_min_dwell_s
                )
            elif pedal_pos != 2:
                self.state = State.DEFAULT_IDLE
                self.pedal_steady_start = None

        # Emit event on state transition
        if self.state != prev_state:
            self._emit_transition(prev_state, self.state, pedal_pos, brake)

    def update_solenoids(self):
        """Update solenoid states based on current conditions."""
        # 1. VVT Solenoid: Active in POWER mode at high RPM
        vvt_active = (self.state == State.MODE1_POWER and self.filtered_rpm > 3500)
        self._set_solenoid("VVT", vvt_active, f"VVT Solenoid {'activated (RPM > 3500)' if vvt_active else 'deactivated (RPM < 3500)'}")

        # 2. Deactivation Solenoid: Active in ECONOMY mode
        deact_active = (self.state == State.MODE2_ECONOMY)
        self._set_solenoid("Deactivation", deact_active, f"Cylinder Deactivation {'engaged' if deact_active else 'disengaged'}")

        # 3. Purge Solenoid: Cycle every 10s for 2s
        cycle_time = self.time % 10.0
        purge_active = (self.state != State.OFF and cycle_time < 2.0)
        self._set_solenoid("Purge", purge_active, f"Purge Solenoid {'opened' if purge_active else 'closed'}")

    def _set_solenoid(self, name: str, active: bool, message: str):
        """Set a solenoid's state and emit an event if it changed."""
        if self.solenoids.get(name) != active:
            self.solenoids[name] = active
            self._emit(EventCategory.SOLENOID, message, solenoid=name, active=active)

    def _emit_transition(self, from_state: State, to_state: State,
                         pedal_pos: int, brake: bool):
        """Emit a human-readable transition event."""
        rpm = round(self.filtered_rpm, 1)

        explanations = {
            (State.OFF, State.DEFAULT_IDLE):
                f"Engine started. Idling at {rpm} RPM.",
            (State.DEFAULT_IDLE, State.MODE1_POWER):
                f"Accelerator pressed — switched to Power mode at {rpm} RPM.",
            (State.MODE1_POWER, State.MODE2_ECONOMY):
                f"Pedal held steady for {self.config.pedal_steady_seconds:.0f}s — "
                f"switched to Economy mode. Cruising target: {rpm} RPM.",
            (State.MODE2_ECONOMY, State.DEFAULT_IDLE):
                (f"Brake applied — returned to Idle at {rpm} RPM."
                 if brake else
                 f"Accelerator released — returned to Idle at {rpm} RPM."),
            (State.MODE1_POWER, State.DEFAULT_IDLE):
                f"Accelerator released — returned to Idle at {rpm} RPM.",
        }

        message = explanations.get(
            (from_state, to_state),
            f"Mode changed from {from_state.value} to {to_state.value} at {rpm} RPM."
        )

        self._emit(
            EventCategory.SWITCH,
            message,
            from_state=from_state.value,
            to_state=to_state.value,
            rpm=rpm,
            pedal_pos=pedal_pos,
            brake=brake,
        )

    # ------------------------------------------------------------------
    # Main step
    # ------------------------------------------------------------------

    def step(self, pedal_pos: int, brake: bool, start_cmd: bool, load: float = 1.0) -> dict:
        """Execute one simulation timestep.  Returns the log entry dict."""
        self.update_state(pedal_pos, brake, start_cmd)
        self.update_solenoids()

        if self.should_fire_pulse():
            self.fire_pulse()

        self.update_rpm_physics(load)
        self.update_hall_sensor()
        self.update_filtered_rpm()

        self.advance_output = compute_advance_output(
            self.filtered_rpm, self.config.advance_table
        )

        log_entry = {
            'time': self.time,
            'state': self.state.value,
            'pedal_pos': pedal_pos,
            'brake': brake,
            'true_rpm': self.true_rpm,
            'measured_rpm': self.measured_rpm,
            'filtered_rpm': self.filtered_rpm,
            'advance_output': self.advance_output,
            'cylinder': self.current_cylinder,
            'standard_target': self.standard_rpm_target if self.standard_rpm_target else 0.0,
            'active_target': self.get_active_rpm_target(),
            'solenoids': self.solenoids.copy(),
            'fuel_consumed': self.fuel_consumed,
            'load': load,
        }
        self.log.append(log_entry)

        self.time += self.config.dt
        return log_entry
