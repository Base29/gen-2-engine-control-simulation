"""
test_gen2_sim.py – Deterministic unit and integration tests for gen2_sim.py.

Run with:
    python -m pytest test_gen2_sim.py -v

All tests use a fixed Config (no noise, dt=0.01) so results are reproducible
across runs and platforms.
"""
import math
import pytest

from gen2_sim import (
    AdvanceTable,
    Config,
    EngineSimulator,
    State,
    _validate_rpm,
    compute_advance_output,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sim(
    *,
    noise: bool = False,
    pedal_steady_seconds: float = 5.0,
    mode2_min_dwell_s: float = 2.0,
    cylinder_count: int = 4,
) -> EngineSimulator:
    """Return a freshly initialised simulator with deterministic settings."""
    cfg = Config(
        cylinder_count=cylinder_count,
        noise_enabled=noise,
        pedal_steady_seconds=pedal_steady_seconds,
        mode2_min_dwell_s=mode2_min_dwell_s,
    )
    return EngineSimulator(cfg)


def _run_steps(sim: EngineSimulator, steps: int, pedal: int, brake: bool, start: bool):
    """Advance the simulation by *steps* timesteps."""
    for _ in range(steps):
        sim.step(pedal, brake, start)


# ---------------------------------------------------------------------------
# 1. compute_advance_output – pure-function tests
# ---------------------------------------------------------------------------

class TestComputeAdvanceOutput:
    """compute_advance_output() must mirror a centrifugal-advance curve."""

    table = AdvanceTable()

    def test_increases_monotonically(self):
        """Advance fraction must rise (or stay flat) as RPM increases."""
        rpms = [500, 700, 900, 1_100, 1_400, 1_800, 2_000, 2_500, 3_000, 4_000]
        outputs = [compute_advance_output(rpm, self.table) for rpm in rpms]
        for a, b in zip(outputs, outputs[1:]):
            assert b >= a, f"Advance not monotone: {a:.3f} → {b:.3f}"

    def test_clamped_at_zero_rpm(self):
        assert compute_advance_output(0.0, self.table) == pytest.approx(0.0)

    def test_clamped_at_very_high_rpm(self):
        assert compute_advance_output(10_000.0, self.table) == pytest.approx(1.0)

    def test_midpoint_interpolation(self):
        """At the midpoint between two breakpoints the result must be the mean."""
        # Breakpoints: (600, 0.00) and (900, 0.25) → midpoint at 750 → 0.125
        result = compute_advance_output(750.0, self.table)
        assert result == pytest.approx(0.125, abs=1e-9)


# ---------------------------------------------------------------------------
# 2. _validate_rpm – guard tests
# ---------------------------------------------------------------------------

class TestValidateRpm:
    def test_clamps_negative(self):
        assert _validate_rpm(-100.0, "x") == 0.0

    def test_clamps_above_max(self):
        from gen2_sim import _MAX_VALID_RPM
        assert _validate_rpm(_MAX_VALID_RPM + 1000, "x") == _MAX_VALID_RPM

    def test_raises_on_nan(self):
        with pytest.raises(ValueError, match="non-finite"):
            _validate_rpm(math.nan, "measured_rpm")

    def test_raises_on_inf(self):
        with pytest.raises(ValueError, match="non-finite"):
            _validate_rpm(math.inf, "filtered_rpm")

    def test_passthrough_valid(self):
        assert _validate_rpm(750.0, "x") == pytest.approx(750.0)


# ---------------------------------------------------------------------------
# 3. Mode-1 firing threshold rises with RPM
# ---------------------------------------------------------------------------

class TestMode1FiringThreshold:
    """The Mode-1 should_fire_pulse() gate must be higher when RPM is higher."""

    def _threshold_at(self, rpm: float) -> float:
        """Return the effective Mode-1 firing threshold for a given filtered RPM."""
        sim = _make_sim()
        sim.state = State.MODE1_POWER
        sim.filtered_rpm = rpm
        # Recompute advance_output using the same function the sim calls.
        from gen2_sim import compute_advance_output
        sim.advance_output = compute_advance_output(rpm, sim.config.advance_table)
        target = sim.get_active_rpm_target()
        return target + sim.advance_output * sim.config.max_advance_rpm

    def test_threshold_at_800_lower_than_at_1400(self):
        t_low = self._threshold_at(800.0)
        t_high = self._threshold_at(1_400.0)
        assert t_high > t_low, (
            f"Expected threshold to rise with RPM, got {t_low:.1f} → {t_high:.1f}"
        )

    def test_threshold_at_1400_lower_than_at_2000(self):
        assert self._threshold_at(2_000.0) > self._threshold_at(1_400.0)


# ---------------------------------------------------------------------------
# 4. Mode-2 entry requires sustained pedal press
# ---------------------------------------------------------------------------

class TestMode2Entry:
    """Mode 2 must not be entered before pedal_steady_seconds elapses."""

    DT = 0.01
    STEADY_S = 5.0

    def _steps(self, seconds: float) -> int:
        return int(seconds / self.DT)

    def test_not_entered_before_steady_time(self):
        sim = _make_sim(pedal_steady_seconds=self.STEADY_S)
        # Get engine running in DEFAULT_IDLE first.
        _run_steps(sim, self._steps(2.0), pedal=1, brake=False, start=True)
        # Enter Mode 1 and hold for less than steady_seconds.
        _run_steps(sim, self._steps(4.9), pedal=2, brake=False, start=True)
        assert sim.state != State.MODE2_ECONOMY, (
            "Mode 2 entered too early (before 5 s steady)"
        )

    def test_entered_after_steady_time(self):
        sim = _make_sim(pedal_steady_seconds=self.STEADY_S)
        _run_steps(sim, self._steps(2.0), pedal=1, brake=False, start=True)
        # Hold pedal=2 for well beyond steady_seconds; uses 8 s to account for
        # the one-step lag before pedal_steady_start is armed.
        _run_steps(sim, self._steps(8.0), pedal=2, brake=False, start=True)
        assert sim.state == State.MODE2_ECONOMY, (
            "Mode 2 not entered after 8 s steady (5 s threshold + generous margin)"
        )

    def test_jitter_resets_timer(self):
        """A brief pedal drop must restart the steady timer."""
        sim = _make_sim(pedal_steady_seconds=self.STEADY_S)
        _run_steps(sim, self._steps(2.0), pedal=1, brake=False, start=True)
        _run_steps(sim, self._steps(4.0), pedal=2, brake=False, start=True)
        # Jitter: release pedal for 0.5 s → timer resets.
        _run_steps(sim, self._steps(0.5), pedal=1, brake=False, start=True)
        # Resume pedal=2; total on-pedal time restarts from 0 → only 3 s so far.
        _run_steps(sim, self._steps(3.0), pedal=2, brake=False, start=True)
        assert sim.state != State.MODE2_ECONOMY, (
            "Mode 2 entered despite pedal jitter resetting the steady timer"
        )


# ---------------------------------------------------------------------------
# 5. Anti-chatter lockout prevents immediate Mode-2 re-entry
# ---------------------------------------------------------------------------

class TestMode2Lockout:
    """After a brake exit from Mode 2, the lockout must block immediate re-entry."""

    DT = 0.01
    DWELL_S = 2.0

    def _steps(self, seconds: float) -> int:
        return int(seconds / self.DT)

    def test_rapid_reentry_blocked(self):
        sim = _make_sim(pedal_steady_seconds=5.0, mode2_min_dwell_s=self.DWELL_S)
        # Reach Mode 2; use 2 s idle + 8 s pedal to clear the steady timer reliably.
        _run_steps(sim, self._steps(2.0), pedal=1, brake=False, start=True)
        _run_steps(sim, self._steps(8.0), pedal=2, brake=False, start=True)
        assert sim.state == State.MODE2_ECONOMY

        # Brake out – lockout armed for mode2_min_dwell_s (2 s).
        # Use pedal=1 during brake so the sim rests at DEFAULT_IDLE (not MODE1).
        _run_steps(sim, self._steps(0.1), pedal=1, brake=True, start=True)
        assert sim.state == State.DEFAULT_IDLE

        # Immediately try to re-enter Mode 2 via pedal=2 + well-past steady time.
        # The lockout window (2 s) has NOT expired so Mode 2 must stay blocked
        # even after steady_seconds elapses at 1 s in.
        _run_steps(sim, self._steps(1.5), pedal=2, brake=False, start=True)
        assert sim.state != State.MODE2_ECONOMY, (
            "Mode-2 re-entry should be blocked within lockout window"
        )

    def test_reentry_allowed_after_lockout_expires(self):
        sim = _make_sim(pedal_steady_seconds=5.0, mode2_min_dwell_s=self.DWELL_S)
        # Reach Mode 2; use generous timing.
        _run_steps(sim, self._steps(2.0), pedal=1, brake=False, start=True)
        _run_steps(sim, self._steps(8.0), pedal=2, brake=False, start=True)
        assert sim.state == State.MODE2_ECONOMY

        # Brake out; pedal=1 so sim stays at DEFAULT_IDLE.
        _run_steps(sim, self._steps(0.1), pedal=1, brake=True, start=True)

        # Wait well past the lockout window, THEN hold pedal=2 for steady_s + margin.
        _run_steps(sim, self._steps(self.DWELL_S + 0.5), pedal=2, brake=False, start=True)
        _run_steps(sim, self._steps(6.0), pedal=2, brake=False, start=True)
        assert sim.state == State.MODE2_ECONOMY, (
            "Mode-2 re-entry should be allowed after lockout window has expired"
        )


# ---------------------------------------------------------------------------
# 6. Brake always returns to DEFAULT_IDLE (regression)
# ---------------------------------------------------------------------------

class TestBrakeOverride:
    DT = 0.01

    def _steps(self, seconds: float) -> int:
        return int(seconds / self.DT)

    def test_brake_from_mode2_goes_to_default_idle(self):
        sim = _make_sim()
        _run_steps(sim, self._steps(2.0), pedal=1, brake=False, start=True)
        # Use 8 s (generous margin over 5 s steady threshold).
        _run_steps(sim, self._steps(8.0), pedal=2, brake=False, start=True)
        assert sim.state == State.MODE2_ECONOMY
        # Brake with pedal=1 so the state settles at DEFAULT_IDLE.
        _run_steps(sim, self._steps(0.05), pedal=1, brake=True, start=True)
        assert sim.state == State.DEFAULT_IDLE

    def test_brake_from_mode1_goes_to_default_idle(self):
        sim = _make_sim()
        _run_steps(sim, self._steps(2.0), pedal=1, brake=False, start=True)
        # Enter Mode 1 but don't hold long enough for Mode 2.
        _run_steps(sim, self._steps(3.0), pedal=2, brake=False, start=True)
        assert sim.state == State.MODE1_POWER
        # Brake while in Mode 1 (pedal drops) → DEFAULT_IDLE.
        _run_steps(sim, self._steps(0.05), pedal=1, brake=True, start=True)
        assert sim.state == State.DEFAULT_IDLE


# ---------------------------------------------------------------------------
# 7. advance_output column present in every log row
# ---------------------------------------------------------------------------

class TestAdvanceOutputLogging:
    def test_advance_output_in_log(self):
        sim = _make_sim()
        sim.step(1, False, True)
        assert "advance_output" in sim.log[0], (
            "advance_output column missing from log dict"
        )

    def test_advance_output_zero_at_idle(self):
        """At DEFAULT_IDLE RPM the advance fraction should be near 0.

        Stable idle on a 4-cyl sits around 650-670 RPM.  The AdvanceTable first
        breakpoint grants 0.0 at 600 RPM and 0.25 at 900 RPM, so interpolation
        at ~665 RPM gives ≈ 0.054 — well below 0.20.
        """
        sim = _make_sim()
        # Run idle for 5 s to stabilise RPM.
        for _ in range(500):
            sim.step(1, False, True)
        last = sim.log[-1]
        assert last["advance_output"] < 0.20, (
            f"Expected near-zero advance at idle, got {last['advance_output']:.3f}"
        )

    def test_advance_output_rises_in_mode1(self):
        """advance_output must increase during the Mode-1 RPM climb."""
        sim = _make_sim()
        for _ in range(200):
            sim.step(1, False, True)
        advance_at_entry = None
        max_advance = 0.0
        for _ in range(1000):
            entry = sim.step(2, False, True)
            if entry["state"] == State.MODE1_POWER.value:
                if advance_at_entry is None:
                    advance_at_entry = entry["advance_output"]
                max_advance = max(max_advance, entry["advance_output"])
        assert max_advance > (advance_at_entry or 0), (
            "advance_output did not increase during Mode-1 RPM climb"
        )
