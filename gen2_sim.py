"""
gen2_sim.py - Gen2 Engine Control Simulation (4 / 6 / 8 Cylinders)

CLI runner and Rich terminal UI.  All simulation logic lives in the
``simulation`` package; this file handles presentation and file I/O only.

Run:
    python gen2_sim.py
"""

import csv
import time
from pathlib import Path
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Re-export core types so existing imports from gen2_sim still work.
from simulation.config import (          # noqa: F401 — public re-exports
    AdvanceTable,
    Config,
    State,
    MAX_VALID_RPM as _MAX_VALID_RPM,
    validate_rpm as _validate_rpm,
    compute_advance_output,
    FIRING_SEQUENCES as _FIRING_SEQUENCES,
    IDLE_RPM as _IDLE_RPM,
)
from simulation.engine import EngineSimulator   # noqa: F401
from simulation.scenarios import SCENARIO_INPUTS as _SCENARIO_INPUTS

# Resolve output directory to the folder that contains this script.
SCRIPT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Optional rich terminal UI
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
except ImportError:
    _RICH = False

console = Console() if _RICH else None

_STATE_STYLE = {
    "OFF":           ("⬛ OFF",            "dim white"),
    "DEFAULT_IDLE":  ("🔵 DEFAULT_IDLE",   "bold cyan"),
    "MODE1_POWER":   ("🔴 MODE1_POWER",    "bold red"),
    "MODE2_ECONOMY": ("🟢 MODE2_ECONOMY",  "bold green"),
}


def _styled_state(state_value: str) -> str:
    label, style = _STATE_STYLE.get(state_value, (state_value, "white"))
    return f"[{style}]{label}[/{style}]"


def print_banner():
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


def save_log(log: list, filename: str):
    """Save simulation log to CSV."""
    if not log:
        return
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=log[0].keys())
        writer.writeheader()
        writer.writerows(log)


def plot_results(log: list, filename: str):
    """Generate matplotlib plot of simulation results."""
    if not log:
        return

    times = [e['time'] for e in log]
    true_rpms = [e['true_rpm'] for e in log]
    filtered_rpms = [e['filtered_rpm'] for e in log]
    states = [e['state'] for e in log]
    active_targets = [e['active_target'] for e in log]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax1.plot(times, true_rpms, label='True RPM', alpha=0.7)
    ax1.plot(times, filtered_rpms, label='Filtered RPM', linewidth=2)
    ax1.plot(times, active_targets, label='Active Target', linestyle='--', color='red')
    ax1.set_ylabel('RPM')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_title('Gen2 Engine Control Simulation')

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
    plt.close(fig)
    print(f"Plot saved to {filename}")


def print_summary(sim: EngineSimulator):
    """Print summary statistics."""
    if not sim.log:
        return

    state_times = {s: 0.0 for s in State}
    for entry in sim.log:
        state_times[State(entry['state'])] += sim.config.dt

    if _RICH:
        table = Table(
            title="[bold yellow]Simulation Summary[/bold yellow]",
            box=box.ROUNDED,
            border_style="yellow",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Metric", style="bold white", min_width=28)
        table.add_column("Value",  style="cyan",       min_width=20)

        table.add_row("Total time",          f"{sim.time:.2f} s")
        table.add_row("Final state",          _styled_state(sim.state.value))
        table.add_row("Final true RPM",       f"{sim.true_rpm:.1f}")
        table.add_row("Final filtered RPM",   f"{sim.filtered_rpm:.1f}")
        target_str = (
            f"{sim.standard_rpm_target:.1f}"
            if sim.standard_rpm_target is not None
            else "[dim]Not set[/dim]"
        )
        table.add_row("Standard RPM target",  target_str)

        dur_table = Table(
            box=box.SIMPLE, show_header=True,
            header_style="bold magenta", padding=(0, 1),
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
        print("\n=== SIMULATION SUMMARY ===")
        print(f"Total time: {sim.time:.2f} seconds")
        print(f"Final state: {sim.state.value}")
        print(f"Final true RPM: {sim.true_rpm:.1f}")
        print(f"Final filtered RPM: {sim.filtered_rpm:.1f}")
        if sim.standard_rpm_target is not None:
            print(f"Standard RPM target: {sim.standard_rpm_target:.1f}")
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
                f"Running {name}", total=total_steps, rpm=0.0, state="---",
            )
            for steps, pedal_pos, brake, start_cmd in all_segments:
                for _ in range(steps):
                    entry = sim.step(pedal_pos, brake, start_cmd)
                    progress.update(
                        task, advance=1,
                        rpm=entry["true_rpm"],
                        state=_STATE_STYLE.get(entry["state"], (entry["state"], ""))[0],
                    )
    else:
        for steps, pedal_pos, brake, start_cmd in all_segments:
            for _ in range(steps):
                sim.step(pedal_pos, brake, start_cmd)

    base_name = name.replace(' ', '_').lower()
    csv_path = str(SCRIPT_DIR / f"{base_name}.csv")
    png_path = str(SCRIPT_DIR / f"{base_name}.png")

    if _RICH:
        console.print(f"  [dim]📄 CSV →[/dim] [underline]{csv_path}[/underline]")
        console.print(f"  [dim]🖼  PNG →[/dim] [underline]{png_path}[/underline]")

    save_log(sim.log, csv_path)
    plot_results(sim.log, png_path)
    print_summary(sim)


SUPPORTED_CYLINDER_COUNTS = [4, 6, 8]


def cleanup_output_files():
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

    all_runs = []
    for cyl in SUPPORTED_CYLINDER_COUNTS:
        config = Config(cylinder_count=cyl)
        for base_name, inputs in _SCENARIO_INPUTS:
            prefixed_name = f"{cyl}cyl_{base_name}"
            all_runs.append((prefixed_name, config, inputs))

    total = len(all_runs)
    for i, (name, config, inputs) in enumerate(all_runs, start=1):
        run_scenario(name, config, inputs, index=i, total=total)

    print_completion_banner(total)


if __name__ == "__main__":
    main()
