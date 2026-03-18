"""
gen2_sim.py - Gen2 Engine Control Simulation (4 / 6 / 8 Cylinders)

STATE MACHINE:
- OFF: Engine not running
- DEFAULT_IDLE: Maintains RPM above idle minimum with intermittent pulses (1 cylinder)
- MODE1_POWER: Pedal position 2 triggers acceleration; frequent pulses (all cylinders in firing order)
- MODE2_ECONOMY: Maintains RPM above captured target with intermittent pulses (1 cylinder, no cooldown)

TRANSITIONS:
- OFF → DEFAULT_IDLE: start_cmd=True (starter provides initial RPM)
- DEFAULT_IDLE → MODE1_POWER: pedal_pos=2
- MODE1_POWER → MODE2_ECONOMY: pedal steady for 5 seconds (standard_rpm_target captured from filtered RPM)
- MODE2_ECONOMY → DEFAULT_IDLE: brake=True (resets economy flags)
- Any state → OFF: start_cmd=False (not used in scenarios)

RPM SIMULATION:
- RPM decays via drag: rpm -= drag * rpm * dt
- Each pulse adds gain: rpm += pulse_gain
- True RPM is the physical simulation value
- Starter motor effect simulated by initial pulses bringing RPM from 0

HALL PULSE GENERATION & MEASUREMENT:
- Hall sensor generates pulses at intervals based on true RPM
- Measured RPM estimated from time between Hall pulses
- Low-pass filter smooths measured RPM: filtered = alpha * measured + (1-alpha) * filtered_prev

CYLINDER FIRING SEQUENCES (0-indexed):
- 4-cyl: 0→2→1→3  (real-world: 1→3→2→4)
- 6-cyl: 0→4→2→5→1→3  (real-world: 1→5→3→6→2→4)
- 8-cyl: 0→7→3→2→5→4→6→1  (real-world: 1→8→4→3→6→5→7→2)

IDLE RPM MINIMUMS (tuned per engine size):
- 4-cyl: 650 RPM
- 6-cyl: 600 RPM
- 8-cyl: 550 RPM

PULSE SCHEDULING:
- Hysteresis: Only fire if RPM drops below (target - hysteresis)
- Cooldown: Minimum time between pulses (0.1s) in DEFAULT_IDLE and MODE1_POWER
- No cooldown in MODE2_ECONOMY for responsive efficiency
- Cylinder selection:
  * DEFAULT_IDLE: Only cylinder 0 (Cylinder 1 in real engine)
  * MODE1_POWER: All cylinders in engine-specific firing sequence
  * MODE2_ECONOMY: Only cylinder 0 (Cylinder 1 in real engine)
"""

import csv
import math
import os
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend – works on all OS (Windows/macOS/Linux)
import matplotlib.pyplot as plt

# Resolve output directory to the folder that contains this script,
# regardless of the working directory the user launches it from.
SCRIPT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# RPM sanity bounds – used by validation helper and AdvanceTable defaults.
# ---------------------------------------------------------------------------
_MAX_VALID_RPM: float = 8_000.0


def _validate_rpm(value: float, name: str) -> float:
    """Return *value* clamped to [0, _MAX_VALID_RPM].

    Raises ValueError for NaN / ±Inf so that corrupt Hall measurements never
    silently propagate into firing decisions.
    """
    if not math.isfinite(value):
        raise ValueError(f"{name} is non-finite: {value!r}")
    return max(0.0, min(value, _MAX_VALID_RPM))

# ---------------------------------------------------------------------------
# Optional rich terminal UI – falls back to plain print() if not installed.
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        Progress, SpinnerColumn, BarColumn,
        TextColumn, TimeElapsedColumn, TaskProgressColumn,
    )
    from rich.table import Table
    from rich.text import Text
    from rich import box
    from rich.rule import Rule
    from rich.style import Style
    _RICH = True
except ImportError:          # pragma: no cover
    _RICH = False

console = Console() if _RICH else None

# State → (label, rich style)
_STATE_STYLE = {
    "OFF":           ("⬛ OFF",            "dim white"),
    "DEFAULT_IDLE":  ("🔵 DEFAULT_IDLE",   "bold cyan"),
    "MODE1_POWER":   ("🔴 MODE1_POWER",    "bold red"),
    "MODE2_ECONOMY": ("🟢 MODE2_ECONOMY",  "bold green"),
}


def _styled_state(state_value: str) -> str:
    """Return a Rich-markup string for a state label, or plain text."""
    label, style = _STATE_STYLE.get(state_value, (state_value, "white"))
    return f"[{style}]{label}[/{style}]"


def print_banner():
    """Display the startup ASCII banner."""
    ascii_art = r"""
  ██████╗ ███████╗███╗   ██╗    ██████╗      ███████╗██╗███╗   ███╗
 ██╔════╝ ██╔════╝████╗  ██║    ╚════██╗     ██╔════╝██║████╗ ████║
 ██║  ███╗█████╗  ██╔██╗ ██║     █████╔╝     ███████╗██║██╔████╔██║
 ██║   ██║██╔══╝  ██║╚██╗██║    ██╔═══╝      ╚════██║██║██║╚██╔╝██║
 ╚██████╔╝███████╗██║ ╚████║    ███████╗     ███████║██║██║ ╚═╝ ██║
  ╚═════╝ ╚══════╝╚═╝  ╚═══╝    ╚══════╝     ╚══════╝╚═╝╚═╝     ╚═╝
               4 / 6 / 8-Cylinder Engine Control Simulation
"""
    if _RICH:
        console.print(Panel(
            Text(ascii_art, style="bold yellow", justify="center"),
            border_style="yellow",
            subtitle="[dim]v2.1  |  Windows · macOS · Linux[/dim]",
            padding=(0, 2),
        ))
    else:
        print(ascii_art)
        print("=" * 68)


def print_scenario_header(name: str, index: int, total: int):
    """Print a styled scenario header."""
    if _RICH:
        console.print()
        console.print(Rule(
            f"[bold white]SCENARIO {index}/{total}  ·  {name}[/bold white]",
            style="yellow",
        ))
    else:
        print(f"\n{'=' * 60}")
        print(f"SCENARIO {index}/{total}: {name}")
        print("=" * 60)


def print_completion_banner(total_scenarios: int):
    """Print a completion banner after all scenarios finish."""
    if _RICH:
        console.print()
        console.print(Panel(
            Text(
                f"✅  All {total_scenarios} scenarios completed successfully!",
                style="bold green",
                justify="center",
            ),
            border_style="green",
            padding=(1, 4),
        ))
    else:
        print("\n" + "=" * 60)
        print(f"ALL {total_scenarios} SCENARIOS COMPLETE")
        print("=" * 60)


class State(Enum):
    OFF = "OFF"
    DEFAULT_IDLE = "DEFAULT_IDLE"
    MODE1_POWER = "MODE1_POWER"
    MODE2_ECONOMY = "MODE2_ECONOMY"


# Default firing sequences per cylinder count (0-indexed).
# 4-cyl:  1→3→2→4  ⟹  0,2,1,3
# 6-cyl:  1→5→3→6→2→4  ⟹  0,4,2,5,1,3
# 8-cyl:  1→8→4→3→6→5→7→2  ⟹  0,7,3,2,5,4,6,1
_FIRING_SEQUENCES = {
    4: (0, 2, 1, 3),
    6: (0, 4, 2, 5, 1, 3),
    8: (0, 7, 3, 2, 5, 4, 6, 1),
}

# Idle RPM minimums tuned per engine displacement / cylinder count.
_IDLE_RPM = {
    4: 650.0,
    6: 600.0,
    8: 550.0,
}


@dataclass
class AdvanceTable:
    """RPM → advance-output lookup table used in MODE1_POWER.

    Each breakpoint is an (rpm, advance_pct) pair where advance_pct is in
    [0.0, 1.0].  Pairs must be sorted by RPM (ascending).  Linear
    interpolation is used between breakpoints, clamped at the extremes.

    The curve below approximates a centrifugal-advance characteristic:
    - Near idle RPM  → little advance (engine not yet loaded)
    - Above ~2 000 RPM → full advance authority
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

    Returns a value in [0.0, 1.0].  This is a pure function with no
    side-effects, making it straightforward to unit-test in isolation.

    Analogy: on a mechanical distributor the centrifugal weights move
    further out as RPM rises, advancing the ignition timing.  Here, the
    returned fraction drives the Mode-1 firing threshold upward so that the
    control system allows higher RPM before cutting pulses – the software
    equivalent of progressive cam / timing advance.
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
            # Linear interpolation between adjacent breakpoints.
            t = (rpm - rpm_lo) / (rpm_hi - rpm_lo)
            return adv_lo + t * (adv_hi - adv_lo)

    return breakpoints[-1][1]  # unreachable, but satisfies type checker


@dataclass
class Config:
    dt: float = 0.01            # timestep in seconds
    cylinder_count: int = 4     # supported: 4, 6, 8
    pedal_steady_seconds: float = 5.0
    drag: float = 0.05          # RPM decay coefficient
    pulse_gain: float = 50.0    # RPM increase per pulse
    hysteresis: float = 50.0    # RPM below target before firing
    cooldown: float = 0.1       # minimum seconds between pulses (not used in Mode 2)
    filter_alpha: float = 0.1   # low-pass filter coefficient
    noise_enabled: bool = False
    noise_seed: int = 42
    # RPM headroom added to idle_min at full advance (replaces bare magic number).
    max_advance_rpm: float = 400.0
    # Anti-chatter: minimum seconds to stay in a mode after any Mode-1 ↔ Mode-2
    # switch.  Prevents rapid oscillation when RPM sits near the boundary.
    mode2_min_dwell_s: float = 2.0
    # Advance-curve lookup table (see AdvanceTable above).
    advance_table: AdvanceTable = field(default_factory=AdvanceTable)
    # Optional overrides – if None, derived automatically from cylinder_count.
    default_idle_rpm_min: float = None          # type: ignore[assignment]
    power_firing_sequence: tuple = None         # type: ignore[assignment]

    def __post_init__(self):
        if self.cylinder_count not in _FIRING_SEQUENCES:
            raise ValueError(
                f"Unsupported cylinder_count={self.cylinder_count}. "
                f"Supported values: {sorted(_FIRING_SEQUENCES.keys())}"
            )
        if self.default_idle_rpm_min is None:
            self.default_idle_rpm_min = _IDLE_RPM[self.cylinder_count]
        if self.power_firing_sequence is None:
            self.power_firing_sequence = _FIRING_SEQUENCES[self.cylinder_count]
        if self.max_advance_rpm <= 0:
            raise ValueError("max_advance_rpm must be positive")
        if self.mode2_min_dwell_s < 0:
            raise ValueError("mode2_min_dwell_s must be non-negative")


class EngineSimulator:
    def __init__(self, config: Config):
        self.config = config
        self.state = State.OFF
        self.true_rpm = 0.0
        self.measured_rpm = 0.0
        self.filtered_rpm = 0.0
        self.current_cylinder = 0
        self.power_sequence_index = 0  # Track position in power firing sequence
        self.last_pulse_time = -999.0
        self.time = 0.0

        # Hall sensor simulation
        self.last_hall_time = 0.0
        self.hall_interval = 0.0

        # RPM-advance compensation output (0.0 = no advance, 1.0 = full advance).
        # Updated every step from the AdvanceTable; exposed in CSV for review.
        self.advance_output: float = 0.0

        # Mode tracking
        self.standard_rpm_target = None
        self.pedal_steady_start = None
        self.last_pedal_pos = 1
        # Anti-chatter lockout: simulation time before a mode-switch is allowed.
        self._mode2_lockout_until: float = 0.0

        # Logging
        self.log: List[dict] = []

        if config.noise_enabled:
            random.seed(config.noise_seed)
    
    def get_active_rpm_target(self) -> float:
        """Return the active RPM target based on state and standard_rpm_target."""
        if self.state == State.MODE2_ECONOMY and self.standard_rpm_target is not None:
            return self.standard_rpm_target
        return self.config.default_idle_rpm_min
    
    def should_fire_pulse(self) -> bool:
        """Determine if a pulse should be fired based on state and conditions."""
        if self.state == State.OFF:
            return False
        
        # Check cooldown (not used in MODE2_ECONOMY)
        if self.state != State.MODE2_ECONOMY:
            if self.time - self.last_pulse_time < self.config.cooldown:
                return False
        
        target = self.get_active_rpm_target()
        
        if self.state == State.MODE1_POWER:
            # Progressive threshold: as RPM rises, advance_output climbs toward
            # 1.0 and the firing threshold rises by up to max_advance_rpm.
            # This mirrors centrifugal/vacuum advance on a mechanical distributor:
            # the system allows higher RPM before backing off pulses.
            threshold = target + self.advance_output * self.config.max_advance_rpm
            return self.filtered_rpm < threshold
        elif self.state in [State.DEFAULT_IDLE, State.MODE2_ECONOMY]:
            # Hysteresis-based firing (1 cylinder at idle/economy)
            return self.filtered_rpm < (target - self.config.hysteresis)

        return False
    
    def fire_pulse(self):
        """Fire a pulse on the current cylinder and advance based on mode."""
        self.true_rpm += self.config.pulse_gain
        self.last_pulse_time = self.time
        
        if self.state == State.MODE1_POWER:
            # Power mode: Use firing sequence 1, 3, 2, 4 (0-indexed: 0, 2, 1, 3)
            self.current_cylinder = self.config.power_firing_sequence[self.power_sequence_index]
            self.power_sequence_index = (self.power_sequence_index + 1) % len(self.config.power_firing_sequence)
        else:
            # Idle/Economy mode: Only cylinder 0 (cylinder 1 in 1-indexed)
            self.current_cylinder = 0
    
    def update_hall_sensor(self):
        """Simulate Hall sensor pulse generation and RPM measurement."""
        if self.true_rpm > 10.0:
            # Hall pulse interval based on true RPM (60 sec/min, pulses per revolution)
            pulses_per_rev = self.config.cylinder_count
            interval = 60.0 / (self.true_rpm * pulses_per_rev)

            if self.time - self.last_hall_time >= interval:
                self.hall_interval = self.time - self.last_hall_time
                self.last_hall_time = self.time

                # Estimate RPM from Hall interval; validate before storing.
                if self.hall_interval > 0:
                    raw = 60.0 / (self.hall_interval * pulses_per_rev)
                    self.measured_rpm = _validate_rpm(raw, "measured_rpm")
        else:
            self.measured_rpm = 0.0

    def update_filtered_rpm(self):
        """Apply low-pass filter to measured RPM, then validate the result."""
        alpha = self.config.filter_alpha
        raw = alpha * self.measured_rpm + (1 - alpha) * self.filtered_rpm
        self.filtered_rpm = _validate_rpm(raw, "filtered_rpm")

    def update_rpm_physics(self):
        """Update true RPM based on drag."""
        self.true_rpm -= self.config.drag * self.true_rpm * self.config.dt
        self.true_rpm = max(0.0, self.true_rpm)
    
    def update_state(self, pedal_pos: int, brake: bool, start_cmd: bool):
        """Update state machine based on inputs."""
        # Track pedal stability
        if pedal_pos != self.last_pedal_pos:
            self.pedal_steady_start = None
        elif pedal_pos == 2 and self.pedal_steady_start is None:
            self.pedal_steady_start = self.time
        self.last_pedal_pos = pedal_pos
        
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
                    # Anti-chatter guard: only switch if we are past the dwell
                    # lockout window set by the previous mode transition.
                    if self.time >= self._mode2_lockout_until:
                        self.standard_rpm_target = self.filtered_rpm
                        self.state = State.MODE2_ECONOMY
                        # Arm the lockout so rapid re-entry is blocked.
                        self._mode2_lockout_until = (
                            self.time + self.config.mode2_min_dwell_s
                        )

        elif self.state == State.MODE2_ECONOMY:
            if brake:
                self.state = State.DEFAULT_IDLE
                self.pedal_steady_start = None
                # Arm lockout: prevents immediately snapping back to Mode 2
                # if the pedal is still at position 2 after the brake release.
                self._mode2_lockout_until = (
                    self.time + self.config.mode2_min_dwell_s
                )
                # Note: standard_rpm_target persists unless explicitly reset
            elif pedal_pos != 2:
                # Driver released the accelerator: return to idle.
                self.state = State.DEFAULT_IDLE
                self.pedal_steady_start = None
            # pedal_pos == 2 while already in Mode 2 → stay in Mode 2 (cruise hold).
            # A fresh re-acceleration demand after releasing the pedal is handled
            # on the subsequent step via the DEFAULT_IDLE → MODE1_POWER transition.
    
    def step(self, pedal_pos: int, brake: bool, start_cmd: bool) -> dict:
        """Execute one simulation timestep."""
        self.update_state(pedal_pos, brake, start_cmd)

        if self.should_fire_pulse():
            self.fire_pulse()

        self.update_rpm_physics()
        self.update_hall_sensor()
        self.update_filtered_rpm()

        # Recompute advance output after RPM is updated so the value logged
        # reflects the state at the *end* of this timestep (matches next step's
        # firing decision).
        self.advance_output = compute_advance_output(
            self.filtered_rpm, self.config.advance_table
        )

        # Log state
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
        }
        self.log.append(log_entry)

        self.time += self.config.dt
        return log_entry
    
    def save_log(self, filename: str):
        """Save simulation log to CSV."""
        if not self.log:
            return
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.log[0].keys())
            writer.writeheader()
            writer.writerows(self.log)
    
    def plot_results(self, filename: str):
        """Generate matplotlib plot of simulation results."""
        if not self.log:
            return
        
        times = [entry['time'] for entry in self.log]
        true_rpms = [entry['true_rpm'] for entry in self.log]
        filtered_rpms = [entry['filtered_rpm'] for entry in self.log]
        states = [entry['state'] for entry in self.log]
        active_targets = [entry['active_target'] for entry in self.log]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # RPM plot
        ax1.plot(times, true_rpms, label='True RPM', alpha=0.7)
        ax1.plot(times, filtered_rpms, label='Filtered RPM', linewidth=2)
        ax1.plot(times, active_targets, label='Active Target', linestyle='--', color='red')
        ax1.set_ylabel('RPM')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_title('Gen2 Engine Control Simulation')
        
        # State plot
        state_map = {s.value: i for i, s in enumerate(State)}
        state_values = [state_map[s] for s in states]
        ax2.plot(times, state_values, drawstyle='steps-post')
        ax2.set_ylabel('State')
        ax2.set_xlabel('Time (s)')
        ax2.set_yticks(list(state_map.values()))
        ax2.set_yticklabels(list(state_map.keys()))
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150)
        plt.close(fig)  # Release figure memory; prevents GUI window pop-ups on Windows
        print(f"Plot saved to {filename}")
    
    def print_summary(self):
        """Print summary statistics."""
        if not self.log:
            return

        # Count state durations
        state_times = {s: 0.0 for s in State}
        for entry in self.log:
            state_times[State(entry['state'])] += self.config.dt

        if _RICH:
            # ── Rich table summary ──────────────────────────────────────────
            table = Table(
                title="[bold yellow]Simulation Summary[/bold yellow]",
                box=box.ROUNDED,
                border_style="yellow",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Metric", style="bold white", min_width=28)
            table.add_column("Value",  style="cyan",       min_width=20)

            table.add_row("Total time",          f"{self.time:.2f} s")
            table.add_row("Final state",          _styled_state(self.state.value))
            table.add_row("Final true RPM",       f"{self.true_rpm:.1f}")
            table.add_row("Final filtered RPM",   f"{self.filtered_rpm:.1f}")
            target_str = (
                f"{self.standard_rpm_target:.1f}"
                if self.standard_rpm_target is not None
                else "[dim]Not set[/dim]"
            )
            table.add_row("Standard RPM target",  target_str)

            # State durations sub-table
            dur_table = Table(
                box=box.SIMPLE,
                show_header=True,
                header_style="bold magenta",
                padding=(0, 1),
            )
            dur_table.add_column("State",    style="bold white")
            dur_table.add_column("Duration", style="cyan")
            for state, duration in state_times.items():
                if duration > 0:
                    label, sty = _STATE_STYLE.get(state.value, (state.value, "white"))
                    dur_table.add_row(f"[{sty}]{label}[/{sty}]", f"{duration:.2f} s")

            console.print(table)
            console.print(dur_table)
        else:
            # ── Plain fallback ──────────────────────────────────────────────
            print("\n=== SIMULATION SUMMARY ===")
            print(f"Total time: {self.time:.2f} seconds")
            print(f"Final state: {self.state.value}")
            print(f"Final true RPM: {self.true_rpm:.1f}")
            print(f"Final filtered RPM: {self.filtered_rpm:.1f}")
            if self.standard_rpm_target is not None:
                print(f"Standard RPM target: {self.standard_rpm_target:.1f}")
            else:
                print("Standard RPM target: Not set")
            print("\nState durations:")
            for state, duration in state_times.items():
                if duration > 0:
                    print(f"  {state.value}: {duration:.2f}s")



def run_scenario(
    name: str,
    config: Config,
    inputs: List[Tuple[float, int, bool, bool]],
    index: int = 1,
    total: int = 1,
):
    """Run a simulation scenario with given inputs."""
    print_scenario_header(name, index, total)

    sim = EngineSimulator(config)

    # Total simulation steps across all input segments
    all_segments = [(int(d / config.dt), p, b, s) for d, p, b, s in inputs]
    total_steps = sum(steps for steps, *_ in all_segments)

    if _RICH:
        with Progress(
            SpinnerColumn(spinner_name="dots", style="yellow"),
            TextColumn("[bold white]{task.description}"),
            BarColumn(bar_width=38, style="yellow", complete_style="green"),
            TaskProgressColumn(),
            TextColumn("[cyan]{task.fields[rpm]:>8.1f} RPM[/cyan]"),
            TextColumn("[dim]{task.fields[state]}[/dim]"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task(
                f"Running {name}",
                total=total_steps,
                rpm=0.0,
                state="---",
            )
            for steps, pedal_pos, brake, start_cmd in all_segments:
                for _ in range(steps):
                    entry = sim.step(pedal_pos, brake, start_cmd)
                    progress.update(
                        task,
                        advance=1,
                        rpm=entry["true_rpm"],
                        state=_STATE_STYLE.get(entry["state"], (entry["state"], ""))[0],
                    )
    else:
        for steps, pedal_pos, brake, start_cmd in all_segments:
            for _ in range(steps):
                sim.step(pedal_pos, brake, start_cmd)

    # Build output paths next to this script so files are always written
    # to the project directory, regardless of the current working directory.
    # This is critical for correct behaviour on Windows when the script is
    # executed via double-click or from an arbitrary directory.
    base_name = name.replace(' ', '_').lower()
    csv_path = str(SCRIPT_DIR / f"{base_name}.csv")
    png_path = str(SCRIPT_DIR / f"{base_name}.png")

    if _RICH:
        console.print(f"  [dim]📄 CSV →[/dim] [underline]{csv_path}[/underline]")
        console.print(f"  [dim]🖼  PNG →[/dim] [underline]{png_path}[/underline]")

    sim.save_log(csv_path)
    sim.plot_results(png_path)
    sim.print_summary()


# Scenario definitions are cylinder-count-agnostic; the same driving sequences
# are reused for every engine variant so results are directly comparable.
_SCENARIO_INPUTS = [
    (
        "1_Start_Idle_Stabilization",
        [
            (10.0, 1, False, True),  # Start and idle for 10 seconds
        ],
    ),
    (
        "2_Power_To_Economy",
        [
            (2.0, 1, False, True),   # Start and stabilize
            (3.0, 2, False, True),   # Pedal to 2, RPM rises
            (6.0, 2, False, True),   # Hold steady for 5+ seconds -> economy mode
            (5.0, 2, False, True),   # Continue in economy
        ],
    ),
    (
        "3_Economy_Brake_Default",
        [
            (2.0, 1, False, True),   # Start
            (3.0, 2, False, True),   # Power mode
            (6.0, 2, False, True),   # Hold steady -> economy
            (3.0, 2, False, True),   # Economy maintenance
            (2.0, 2, True,  True),   # Brake -> back to default idle
            (3.0, 1, False, True),   # Continue in default idle
        ],
    ),
    (
        "4_Pedal_Jitter_Mode1",
        [
            (2.0, 1, False, True),   # Start
            (2.0, 2, False, True),   # Pedal to 2
            (1.0, 1, False, True),   # Jitter: back to 1
            (2.0, 2, False, True),   # Back to 2
            (1.5, 1, False, True),   # Jitter again
            (3.0, 2, False, True),   # Back to 2 (never steady for 5 sec)
        ],
    ),
]

# Cylinder counts to simulate.  Add or remove values here to change the run.
SUPPORTED_CYLINDER_COUNTS = [4, 6, 8]


def cleanup_output_files():
    """Delete any existing simulation CSV/PNG output files before a fresh run.

    Only files whose names begin with a known cylinder-count prefix (e.g.
    '4cyl_', '6cyl_', '8cyl_') are removed, so unrelated project files are
    left untouched.
    """
    prefixes = tuple(f"{cyl}cyl_" for cyl in SUPPORTED_CYLINDER_COUNTS)
    removed: list[Path] = []

    for ext in ("*.csv", "*.png"):
        for path in SCRIPT_DIR.glob(ext):
            if path.name.startswith(prefixes):
                path.unlink()
                removed.append(path)

    if removed:
        if _RICH:
            console.print(
                f"  [dim]🗑  Removed {len(removed)} stale output file"
                f"{'s' if len(removed) != 1 else ''}[/dim]"
            )
        else:
            print(f"Removed {len(removed)} stale output file(s) before starting.")


def main():
    print_banner()
    cleanup_output_files()

    # Build the full list of (scenario_name, config, inputs) tuples, one per
    # cylinder-count × scenario combination, so all variants are run in order.
    all_runs = []
    for cyl in SUPPORTED_CYLINDER_COUNTS:
        config = Config(cylinder_count=cyl)
        for base_name, inputs in _SCENARIO_INPUTS:
            # Prefix the scenario name with the cylinder count so output files
            # from different engine variants never overwrite each other.
            prefixed_name = f"{cyl}cyl_{base_name}"
            all_runs.append((prefixed_name, config, inputs))

    total = len(all_runs)
    for i, (name, config, inputs) in enumerate(all_runs, start=1):
        run_scenario(name, config, inputs, index=i, total=total)

    print_completion_banner(total)


if __name__ == "__main__":
    main()
