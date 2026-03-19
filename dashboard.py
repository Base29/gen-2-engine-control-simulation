"""
dashboard.py — Engine Timing Simulation Dashboard

A professional Streamlit dashboard for interacting with the Gen2 engine
control simulation.  Designed for non-technical users.

Run:
    streamlit run dashboard.py
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from simulation import (
    Config,
    SimulationController,
    SCENARIO_PRESETS,
    State,
)
from simulation.events import EventCategory

# ── Page configuration ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Engine Timing Simulation Dashboard",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* --- Global theme --- */
    .block-container { padding-top: 1rem; }

    /* --- Status badges --- */
    .status-badge {
        display: inline-block;
        padding: 6px 18px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.5px;
    }
    .badge-green  { background: #0e6b30; color: #b7f5c8; }
    .badge-yellow { background: #7a6200; color: #ffe082; }
    .badge-red    { background: #8b1a1a; color: #ffb3b3; }
    .badge-blue   { background: #1a4f8b; color: #b3d4ff; }
    .badge-gray   { background: #3a3a3a; color: #c0c0c0; }

    /* --- Mode badge (large) --- */
    .mode-badge {
        font-size: 1.6rem;
        font-weight: 800;
        padding: 14px 28px;
        border-radius: 16px;
        text-align: center;
        margin: 8px 0 16px 0;
    }
    .mode-off      { background: linear-gradient(135deg, #2a2a2a, #3d3d3d); color: #888; }
    .mode-idle     { background: linear-gradient(135deg, #0d47a1, #1565c0); color: #bbdefb; }
    .mode-power    { background: linear-gradient(135deg, #b71c1c, #d32f2f); color: #ffcdd2; }
    .mode-economy  { background: linear-gradient(135deg, #1b5e20, #2e7d32); color: #c8e6c9; }

    /* --- Explanation panel --- */
    .explanation-panel {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-left: 4px solid #00bcd4;
        padding: 16px 20px;
        border-radius: 8px;
        margin: 12px 0;
        font-size: 1.05rem;
        line-height: 1.5;
    }

    /* --- Event log --- */
    .event-row {
        padding: 6px 12px;
        border-radius: 6px;
        margin: 3px 0;
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 0.82rem;
    }
    .event-info    { background: #1a2332; border-left: 3px solid #4fc3f7; }
    .event-switch  { background: #1a2a1a; border-left: 3px solid #66bb6a; }
    .event-warning { background: #2a2a1a; border-left: 3px solid #ffa726; }
    .event-system  { background: #1a1a2a; border-left: 3px solid #9575cd; }

    /* --- Metric improvements --- */
    [data-testid="stMetricValue"] { font-size: 1.4rem; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem; }

    div[data-testid="stHorizontalBlock"] > div {
        padding: 0 4px;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# Session State Initialisation
# ══════════════════════════════════════════════════════════════════════

def _init_session_state():
    """Initialise all session state keys on first run."""
    defaults = {
        "controller": None,
        "history": [],
        "events": [],
        "sim_state": None,
        "is_running": False,
        "explanation": "Press **Start** to begin the simulation.",
        # Control defaults
        "cylinder_count": 4,
        "rpm_target": 650,
        "pedal_pos": 1,
        "brake": False,
        "start_cmd": True,
        "auto_mode_switch": True,
        "rpm_validation": True,
        "anti_chatter": True,
        # Timing parameters
        "pedal_steady_seconds": 5.0,
        "max_advance_rpm": 400.0,
        "mode2_min_dwell_s": 2.0,
        "hysteresis": 50.0,
        "pulse_gain": 50.0,
        "drag": 0.05,
        # Steps per tick
        "steps_per_tick": 50,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_session_state()


def _get_controller() -> SimulationController:
    """Return or create the simulation controller."""
    if st.session_state.controller is None:
        cfg = _build_config()
        ctrl = SimulationController(cfg)
        ctrl.reset()
        st.session_state.controller = ctrl
    return st.session_state.controller


def _build_config() -> Config:
    """Build a Config from current session state values."""
    return Config(
        cylinder_count=st.session_state.cylinder_count,
        pedal_steady_seconds=st.session_state.pedal_steady_seconds,
        max_advance_rpm=st.session_state.max_advance_rpm,
        mode2_min_dwell_s=st.session_state.mode2_min_dwell_s,
        hysteresis=st.session_state.hysteresis,
        pulse_gain=st.session_state.pulse_gain,
        drag=st.session_state.drag,
    )


# ══════════════════════════════════════════════════════════════════════
# HEADER SECTION
# ══════════════════════════════════════════════════════════════════════

st.markdown("# 🏎️ Engine Timing Simulation Dashboard")
st.markdown(
    "_Visualise and control the ignition timing of a simulated engine "
    "in real time. Adjust inputs, run scenarios, and observe how the "
    "engine responds — no technical knowledge required._"
)

ctrl = _get_controller()
sim_state = ctrl.get_state()

# Status metric cards
def _rpm_delta():
    if len(st.session_state.history) >= 2:
        prev = st.session_state.history[-2]["filtered_rpm"]
        curr = st.session_state.history[-1]["filtered_rpm"]
        return f"{curr - prev:+.1f}"
    return None

_MODE_LABELS = {
    "OFF": "🔴 Off",
    "DEFAULT_IDLE": "🔵 Idle",
    "MODE1_POWER": "🟠 Power",
    "MODE2_ECONOMY": "🟢 Economy",
}

_RPM_STATUS = "✅ Valid" if sim_state.rpm_valid else "❌ Invalid"
_SYS_STATUS = "▶️ Running" if st.session_state.is_running else "⏸️ Paused"

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("RPM", f"{sim_state.filtered_rpm:.0f}", _rpm_delta())
m2.metric("Active Mode", _MODE_LABELS.get(sim_state.state, sim_state.state))
m3.metric("Advance", f"{sim_state.advance_output:.0%}")
m4.metric("RPM Status", _RPM_STATUS)
m5.metric("System State", _SYS_STATUS)

st.divider()

# ══════════════════════════════════════════════════════════════════════
# CONTROLS (left) | LIVE STATE (right)
# ══════════════════════════════════════════════════════════════════════

col_controls, col_state = st.columns([1, 1], gap="large")

# ── LEFT PANEL — Simulation Controls ──────────────────────────────────

with col_controls:
    st.subheader("🎛️ Simulation Controls")

    # A. Primary controls
    btn_cols = st.columns(3)
    with btn_cols[0]:
        start_clicked = st.button(
            "▶️ Start", width="stretch", type="primary",
            help="Begin or resume the simulation"
        )
    with btn_cols[1]:
        pause_clicked = st.button(
            "⏸️ Pause", width="stretch",
            help="Pause the simulation (keep current state)"
        )
    with btn_cols[2]:
        reset_clicked = st.button(
            "🔄 Reset", width="stretch",
            help="Reset the simulation to its initial state"
        )

    # B. Inputs
    st.markdown("#### Engine Inputs")

    input_c1, input_c2 = st.columns(2)
    with input_c1:
        accel_on = st.toggle(
            "🟢 Accelerator",
            value=(st.session_state.pedal_pos == 2),
            help="Turn ON to press the accelerator (engine speeds up). "
                 "Turn OFF to release it (engine returns to idle)."
        )
        st.session_state.pedal_pos = 2 if accel_on else 1
    with input_c2:
        st.session_state.brake = st.toggle(
            "🔴 Brake",
            value=st.session_state.brake,
            help="Turn ON to apply the brake (safety override — returns engine to idle)"
        )

    eng_c1, eng_c2 = st.columns(2)
    with eng_c1:
        new_cyl = st.selectbox(
            "Engine Type",
            options=[4, 6, 8],
            index=[4, 6, 8].index(st.session_state.cylinder_count),
            format_func=lambda x: f"{x}-Cylinder Engine",
            help="Number of cylinders in the engine"
        )
    with eng_c2:
        st.session_state.steps_per_tick = st.slider(
            "Simulation Speed",
            min_value=10, max_value=200, value=st.session_state.steps_per_tick,
            step=10,
            help="How many calculation steps to run per update (higher = faster)"
        )

    # Engine type change requires reset
    if new_cyl != st.session_state.cylinder_count:
        st.session_state.cylinder_count = new_cyl
        cfg = _build_config()
        ctrl.reset(cfg)
        st.session_state.history = []
        st.session_state.is_running = False
        st.session_state.explanation = f"Engine changed to **{new_cyl}-cylinder**. Press Start."

    # C. Advanced parameters
    with st.expander("⚙️ Advanced Parameters", expanded=False):
        adv_c1, adv_c2 = st.columns(2)
        with adv_c1:
            st.session_state.pedal_steady_seconds = st.slider(
                "Time to enter Economy mode (seconds)",
                min_value=1.0, max_value=15.0,
                value=st.session_state.pedal_steady_seconds,
                step=0.5,
                help="How long the accelerator must be held steady before switching to Economy mode"
            )
            st.session_state.hysteresis = st.slider(
                "RPM Sensitivity (hysteresis)",
                min_value=10.0, max_value=100.0,
                value=st.session_state.hysteresis,
                step=5.0,
                help="How far RPM must drop below target before the engine fires again"
            )
            st.session_state.pulse_gain = st.slider(
                "Engine Power (RPM per pulse)",
                min_value=10.0, max_value=100.0,
                value=st.session_state.pulse_gain,
                step=5.0,
                help="How much RPM increases each time a cylinder fires"
            )
        with adv_c2:
            st.session_state.max_advance_rpm = st.slider(
                "Maximum Advance (RPM headroom)",
                min_value=100.0, max_value=1000.0,
                value=st.session_state.max_advance_rpm,
                step=50.0,
                help="Maximum RPM boost from the advance compensation system"
            )
            st.session_state.mode2_min_dwell_s = st.slider(
                "Anti-chatter guard (seconds)",
                min_value=0.0, max_value=5.0,
                value=st.session_state.mode2_min_dwell_s,
                step=0.5,
                help="Minimum time to wait before allowing another mode switch"
            )
            st.session_state.drag = st.slider(
                "Engine Drag (resistance)",
                min_value=0.01, max_value=0.20,
                value=st.session_state.drag,
                step=0.01,
                help="How quickly RPM drops when no cylinders fire"
            )

    # D. Scenario Presets
    st.markdown("#### 📋 Scenario Presets")
    st.caption("Select a preset to automatically run a complete engine scenario.")

    preset_cols = st.columns(3)
    for i, preset in enumerate(SCENARIO_PRESETS):
        col = preset_cols[i % 3]
        with col:
            if st.button(
                preset.label,
                key=f"preset_{preset.name}",
                width="stretch",
                help=preset.description,
            ):
                cfg = _build_config()
                ctrl.reset(cfg)
                results = ctrl.run_scenario(preset, cfg)
                st.session_state.history = results
                st.session_state.events = ctrl.get_events()
                st.session_state.is_running = False
                state = ctrl.get_state()
                st.session_state.explanation = (
                    f"✅ **{preset.label}** scenario complete. "
                    f"Final state: **{_MODE_LABELS.get(state.state, state.state)}** "
                    f"at **{state.filtered_rpm:.0f} RPM**."
                )
                st.rerun()


# ── RIGHT PANEL — Live Engine State ───────────────────────────────────

with col_state:
    st.subheader("🔍 Live Engine State")

    # 1. Active Mode (large badge)
    badge_class = {
        "OFF": "mode-off",
        "DEFAULT_IDLE": "mode-idle",
        "MODE1_POWER": "mode-power",
        "MODE2_ECONOMY": "mode-economy",
    }
    mode_text = {
        "OFF": "⬛  ENGINE OFF",
        "DEFAULT_IDLE": "🔵  IDLE MODE",
        "MODE1_POWER": "🔴  POWER MODE",
        "MODE2_ECONOMY": "🟢  ECONOMY MODE",
    }
    st.markdown(
        f'<div class="mode-badge {badge_class.get(sim_state.state, "mode-off")}">'
        f'{mode_text.get(sim_state.state, sim_state.state)}</div>',
        unsafe_allow_html=True,
    )

    # 2. Status indicators
    ind_cols = st.columns(2)
    with ind_cols[0]:
        st.markdown(
            f'<span class="status-badge {"badge-green" if sim_state.rpm_valid else "badge-red"}">'
            f'{"✅ RPM Valid" if sim_state.rpm_valid else "❌ RPM Invalid"}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<span class="status-badge {"badge-yellow" if sim_state.compensation_active else "badge-gray"}">'
            f'{"⚡ Advance Active" if sim_state.compensation_active else "— Advance Off"}</span>',
            unsafe_allow_html=True,
        )
    with ind_cols[1]:
        st.markdown(
            f'<span class="status-badge {"badge-blue" if sim_state.anti_chatter_active else "badge-gray"}">'
            f'{"🛡️ Anti-Chatter On" if sim_state.anti_chatter_active else "— Guard Off"}</span>',
            unsafe_allow_html=True,
        )
        # Detect if a switch just happened
        events = ctrl.get_events()
        recent_switch = any(
            e.category == EventCategory.SWITCH and e.time >= sim_state.time - 0.1
            for e in events[-5:]
        ) if events else False
        st.markdown(
            f'<span class="status-badge {"badge-green" if recent_switch else "badge-gray"}">'
            f'{"🔀 Switch Triggered" if recent_switch else "— No Switch"}</span>',
            unsafe_allow_html=True,
        )

    # 3. Explanation panel (MANDATORY)
    st.markdown("#### 💡 What's Happening")
    st.markdown(
        f'<div class="explanation-panel">{st.session_state.explanation}</div>',
        unsafe_allow_html=True,
    )

    # Extra details
    with st.expander("📊 Detailed State", expanded=False):
        det_c1, det_c2 = st.columns(2)
        with det_c1:
            st.metric("True RPM", f"{sim_state.true_rpm:.1f}")
            st.metric("Measured RPM", f"{sim_state.measured_rpm:.1f}")
            st.metric("Filtered RPM", f"{sim_state.filtered_rpm:.1f}")
        with det_c2:
            st.metric("Active Target", f"{sim_state.active_target:.0f} RPM")
            st.metric("Cruise Target", f"{sim_state.standard_rpm_target:.0f} RPM")
            st.metric("Simulation Time", f"{sim_state.time:.2f}s")


# ══════════════════════════════════════════════════════════════════════
# Handle button actions
# ══════════════════════════════════════════════════════════════════════

if start_clicked:
    st.session_state.is_running = True
    ctrl.start()
    st.session_state.explanation = "▶️ Simulation **running**. The engine is active."

if pause_clicked:
    st.session_state.is_running = False
    ctrl.pause()
    st.session_state.explanation = "⏸️ Simulation **paused**. Press Start to continue."

if reset_clicked:
    cfg = _build_config()
    ctrl.reset(cfg)
    st.session_state.history = []
    st.session_state.events = []
    st.session_state.is_running = False
    st.session_state.explanation = "🔄 Simulation **reset**. Ready to start."
    st.rerun()


# ══════════════════════════════════════════════════════════════════════
# Run simulation steps if running
# ══════════════════════════════════════════════════════════════════════

if st.session_state.is_running:
    # Build config if params changed
    cfg = _build_config()
    if (cfg.pedal_steady_seconds != ctrl.config.pedal_steady_seconds or
        cfg.max_advance_rpm != ctrl.config.max_advance_rpm or
        cfg.hysteresis != ctrl.config.hysteresis or
        cfg.pulse_gain != ctrl.config.pulse_gain or
        cfg.drag != ctrl.config.drag or
        cfg.mode2_min_dwell_s != ctrl.config.mode2_min_dwell_s):
        # Parameter changed but don't reset — just update config for next reset
        pass

    results = ctrl.run_steps(
        st.session_state.steps_per_tick,
        pedal_pos=st.session_state.pedal_pos,
        brake=st.session_state.brake,
        start_cmd=st.session_state.start_cmd,
    )
    st.session_state.history = ctrl.get_history()
    st.session_state.events = ctrl.get_events()

    # Update explanation from latest events
    switch_events = [e for e in ctrl.get_events() if e.category == EventCategory.SWITCH]
    if switch_events:
        last_switch = switch_events[-1]
        st.session_state.explanation = f"🔀 {last_switch.message}"
    else:
        state = ctrl.get_state()
        if state.state == "DEFAULT_IDLE":
            st.session_state.explanation = (
                f"Engine is idling at **{state.filtered_rpm:.0f} RPM**. "
                f"One cylinder fires intermittently to hold RPM above "
                f"**{state.active_target:.0f} RPM**."
            )
        elif state.state == "MODE1_POWER":
            st.session_state.explanation = (
                f"All cylinders are firing in sequence. RPM is climbing at "
                f"**{state.filtered_rpm:.0f} RPM**. Advance compensation is at "
                f"**{state.advance_output:.0%}**."
            )
        elif state.state == "MODE2_ECONOMY":
            st.session_state.explanation = (
                f"Economy mode — maintaining cruise at **{state.standard_rpm_target:.0f} RPM** "
                f"target. Only one cylinder fires for efficiency."
            )
        elif state.state == "OFF":
            st.session_state.explanation = "Engine is **off**. Press Start to begin."


# ══════════════════════════════════════════════════════════════════════
# CHARTS SECTION (full width)
# ══════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📈 Performance Charts")

history = st.session_state.history

if history and len(history) > 1:
    times = [h["time"] for h in history]
    true_rpms = [h["true_rpm"] for h in history]
    filtered_rpms = [h["filtered_rpm"] for h in history]
    advance_outputs = [h["advance_output"] for h in history]
    states = [h["state"] for h in history]
    active_targets = [h["active_target"] for h in history]

    # Detect mode switch points
    switch_times = []
    switch_labels = []
    for i in range(1, len(states)):
        if states[i] != states[i - 1]:
            switch_times.append(times[i])
            switch_labels.append(f"{states[i-1]} → {states[i]}")

    # Map states to numeric values for step plot
    state_order = ["OFF", "DEFAULT_IDLE", "MODE1_POWER", "MODE2_ECONOMY"]
    state_nums = [state_order.index(s) if s in state_order else 0 for s in states]

    # Build combined figure with 3 subplots
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=("Engine Speed (RPM)", "Advance Compensation", "Engine Mode"),
        row_heights=[0.45, 0.25, 0.30],
    )

    # --- RPM chart ---
    fig.add_trace(go.Scatter(
        x=times, y=true_rpms,
        name="True RPM", mode="lines",
        line=dict(color="#64b5f6", width=1.5),
        opacity=0.6,
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=times, y=filtered_rpms,
        name="Filtered RPM", mode="lines",
        line=dict(color="#42a5f5", width=2.5),
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=times, y=active_targets,
        name="Target RPM", mode="lines",
        line=dict(color="#ef5350", width=2, dash="dash"),
    ), row=1, col=1)

    # --- Advance chart ---
    fig.add_trace(go.Scatter(
        x=times, y=advance_outputs,
        name="Advance Output", mode="lines",
        line=dict(color="#ffa726", width=2),
        fill="tozeroy",
        fillcolor="rgba(255, 167, 38, 0.15)",
    ), row=2, col=1)

    # --- Mode chart (step plot) ---
    fig.add_trace(go.Scatter(
        x=times, y=state_nums,
        name="Mode", mode="lines",
        line=dict(color="#66bb6a", width=2.5, shape="hv"),
    ), row=3, col=1)

    # Add mode switch annotations
    for st_time, st_label in zip(switch_times, switch_labels):
        fig.add_vline(
            x=st_time, line_dash="dot",
            line_color="rgba(255, 255, 255, 0.3)",
            row="all", col=1,
        )

    # Axis labels & styling
    fig.update_yaxes(title_text="RPM", row=1, col=1)
    fig.update_yaxes(title_text="Advance %", row=2, col=1,
                     tickformat=".0%", range=[-0.05, 1.1])
    fig.update_yaxes(
        title_text="Mode", row=3, col=1,
        tickvals=[0, 1, 2, 3],
        ticktext=["Off", "Idle", "Power", "Economy"],
    )
    fig.update_xaxes(title_text="Time (seconds)", row=3, col=1)

    fig.update_layout(
        height=700,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10,10,30,0.5)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=40, b=40),
        font=dict(size=12),
    )

    st.plotly_chart(fig, width="stretch", key="main_chart")

else:
    st.info(
        "📊 Charts will appear here once the simulation runs. "
        "Press **Start** or select a **Scenario Preset** above."
    )


# ══════════════════════════════════════════════════════════════════════
# EVENT LOG (left) | EXPORT (right)
# ══════════════════════════════════════════════════════════════════════

st.divider()
col_log, col_export = st.columns([2, 1], gap="large")

# ── Event Log Panel ───────────────────────────────────────────────────

with col_log:
    st.subheader("📋 Event Log")

    events = st.session_state.events
    if events:
        event_class_map = {
            EventCategory.INFO: "event-info",
            EventCategory.SWITCH: "event-switch",
            EventCategory.WARNING: "event-warning",
            EventCategory.SYSTEM: "event-system",
        }

        # Show most recent first, up to 50 events
        display_events = list(reversed(events[-50:]))
        event_html = ""
        for ev in display_events:
            cls = event_class_map.get(ev.category, "event-info")
            badge = ev.category.value
            event_html += (
                f'<div class="event-row {cls}">'
                f'<strong>{ev.time:8.2f}s</strong> '
                f'<code>{badge}</code> '
                f'{ev.message}'
                f'</div>'
            )
        st.markdown(event_html, unsafe_allow_html=True)
    else:
        st.caption("No events recorded yet. Start a simulation to see events here.")


# ── Export Panel ──────────────────────────────────────────────────────

with col_export:
    st.subheader("💾 Export Data")

    if history:
        csv_data = ctrl.export_csv()
        st.download_button(
            "📄 Download Simulation Data (CSV)",
            data=csv_data,
            file_name=f"engine_simulation_{st.session_state.cylinder_count}cyl.csv",
            mime="text/csv",
            width="stretch",
        )

        events_log = ctrl.export_events_log()
        st.download_button(
            "📋 Download Event Log",
            data=events_log,
            file_name="engine_events.log",
            mime="text/plain",
            width="stretch",
        )

        scenario_json = ctrl.export_scenario()
        st.download_button(
            "💾 Save Scenario (JSON)",
            data=scenario_json,
            file_name="engine_scenario.json",
            mime="application/json",
            width="stretch",
        )
    else:
        st.caption(
            "Run a simulation first, then use these buttons to download your results."
        )

    st.markdown("---")
    st.caption(
        "**Tip:** Select a Scenario Preset to quickly run a complete "
        "engine test sequence, then download the results."
    )


# ══════════════════════════════════════════════════════════════════════
# Auto-rerun while running
# ══════════════════════════════════════════════════════════════════════

if st.session_state.is_running:
    import time
    time.sleep(0.1)
    st.rerun()
