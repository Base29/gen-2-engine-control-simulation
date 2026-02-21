"""
gen2_sim.py - Gen2 4-Cylinder Engine Control Simulation

STATE MACHINE:
- OFF: Engine not running
- DEFAULT_IDLE: Maintains RPM above default_idle_rpm_min with intermittent pulses
- MODE1_POWER: Pedal position 2 triggers acceleration; frequent pulses while pedal unstable
- MODE2_ECONOMY: Maintains RPM above active minimum (default idle or standard target) with intermittent pulses

TRANSITIONS:
- OFF -> DEFAULT_IDLE: start_cmd=True
- DEFAULT_IDLE -> MODE1_POWER: pedal_pos=2
- MODE1_POWER -> MODE2_ECONOMY: pedal steady for 5 seconds (standard_rpm_target set from filtered RPM)
- MODE2_ECONOMY -> DEFAULT_IDLE: brake=True (resets economy flags)
- Any state -> OFF: start_cmd=False (not used in scenarios)

RPM SIMULATION:
- RPM decays via drag: rpm -= drag * rpm * dt
- Each pulse adds gain: rpm += pulse_gain
- True RPM is the physical simulation value

HALL PULSE GENERATION & MEASUREMENT:
- Hall sensor generates pulses at intervals based on true RPM
- Measured RPM estimated from time between Hall pulses
- Low-pass filter smooths measured RPM: filtered = alpha * measured + (1-alpha) * filtered_prev

PULSE SCHEDULING:
- Hysteresis: Only fire if RPM drops below (target - hysteresis)
- Cooldown: Minimum time between pulses to prevent over-firing
- Round-robin: Cylinders fire in sequence (0,1,2,3,0,...)
- MODE1_POWER: More frequent pulses (simulates recorded activation sequence)
- MODE2_ECONOMY: Intermittent pulses only when needed
"""

import csv
import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

import matplotlib.pyplot as plt


class State(Enum):
    OFF = "OFF"
    DEFAULT_IDLE = "DEFAULT_IDLE"
    MODE1_POWER = "MODE1_POWER"
    MODE2_ECONOMY = "MODE2_ECONOMY"


@dataclass
class Config:
    dt: float = 0.01  # timestep in seconds
    cylinder_count: int = 4
    default_idle_rpm_min: float = 800.0
    pedal_steady_seconds: float = 5.0
    drag: float = 0.05  # RPM decay coefficient
    pulse_gain: float = 50.0  # RPM increase per pulse
    hysteresis: float = 50.0  # RPM below target before firing
    cooldown: float = 0.1  # minimum seconds between pulses
    filter_alpha: float = 0.1  # low-pass filter coefficient
    noise_enabled: bool = False
    noise_seed: int = 42


class EngineSimulator:
    def __init__(self, config: Config):
        self.config = config
        self.state = State.OFF
        self.true_rpm = 0.0
        self.measured_rpm = 0.0
        self.filtered_rpm = 0.0
        self.current_cylinder = 0
        self.last_pulse_time = -999.0
        self.time = 0.0
        
        # Hall sensor simulation
        self.last_hall_time = 0.0
        self.hall_interval = 0.0
        
        # Mode tracking
        self.standard_rpm_target = None
        self.pedal_steady_start = None
        self.last_pedal_pos = 1
        
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
        
        # Check cooldown
        if self.time - self.last_pulse_time < self.config.cooldown:
            return False
        
        target = self.get_active_rpm_target()
        
        if self.state == State.MODE1_POWER:
            # More aggressive firing in power mode
            return self.filtered_rpm < target + 200.0
        elif self.state in [State.DEFAULT_IDLE, State.MODE2_ECONOMY]:
            # Hysteresis-based firing
            return self.filtered_rpm < (target - self.config.hysteresis)
        
        return False
    
    def fire_pulse(self):
        """Fire a pulse on the current cylinder and advance round-robin."""
        self.true_rpm += self.config.pulse_gain
        self.last_pulse_time = self.time
        self.current_cylinder = (self.current_cylinder + 1) % self.config.cylinder_count
    
    def update_hall_sensor(self):
        """Simulate Hall sensor pulse generation and RPM measurement."""
        if self.true_rpm > 10.0:
            # Hall pulse interval based on true RPM (60 sec/min, pulses per revolution)
            pulses_per_rev = self.config.cylinder_count
            interval = 60.0 / (self.true_rpm * pulses_per_rev)
            
            if self.time - self.last_hall_time >= interval:
                self.hall_interval = self.time - self.last_hall_time
                self.last_hall_time = self.time
                
                # Estimate RPM from Hall interval
                if self.hall_interval > 0:
                    self.measured_rpm = 60.0 / (self.hall_interval * pulses_per_rev)
        else:
            self.measured_rpm = 0.0
    
    def update_filtered_rpm(self):
        """Apply low-pass filter to measured RPM."""
        alpha = self.config.filter_alpha
        self.filtered_rpm = alpha * self.measured_rpm + (1 - alpha) * self.filtered_rpm
    
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
                    # Transition to economy mode
                    self.standard_rpm_target = self.filtered_rpm
                    self.state = State.MODE2_ECONOMY
        
        elif self.state == State.MODE2_ECONOMY:
            if brake:
                self.state = State.DEFAULT_IDLE
                self.pedal_steady_start = None
                # Note: standard_rpm_target persists unless explicitly reset
            elif pedal_pos == 2:
                self.state = State.MODE1_POWER
                self.pedal_steady_start = None
    
    def step(self, pedal_pos: int, brake: bool, start_cmd: bool) -> dict:
        """Execute one simulation timestep."""
        self.update_state(pedal_pos, brake, start_cmd)
        
        if self.should_fire_pulse():
            self.fire_pulse()
        
        self.update_rpm_physics()
        self.update_hall_sensor()
        self.update_filtered_rpm()
        
        # Log state
        log_entry = {
            'time': self.time,
            'state': self.state.value,
            'pedal_pos': pedal_pos,
            'brake': brake,
            'true_rpm': self.true_rpm,
            'measured_rpm': self.measured_rpm,
            'filtered_rpm': self.filtered_rpm,
            'cylinder': self.current_cylinder,
            'standard_target': self.standard_rpm_target if self.standard_rpm_target else 0.0,
            'active_target': self.get_active_rpm_target()
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
        print(f"Plot saved to {filename}")
    
    def print_summary(self):
        """Print summary statistics."""
        if not self.log:
            return
        
        print("\n=== SIMULATION SUMMARY ===")
        print(f"Total time: {self.time:.2f} seconds")
        print(f"Final state: {self.state.value}")
        print(f"Final true RPM: {self.true_rpm:.1f}")
        print(f"Final filtered RPM: {self.filtered_rpm:.1f}")
        if self.standard_rpm_target is not None:
            print(f"Standard RPM target: {self.standard_rpm_target:.1f}")
        else:
            print("Standard RPM target: Not set")
        
        # Count state durations
        state_times = {s: 0.0 for s in State}
        for entry in self.log:
            state_times[State(entry['state'])] += self.config.dt
        
        print("\nState durations:")
        for state, duration in state_times.items():
            if duration > 0:
                print(f"  {state.value}: {duration:.2f}s")



def run_scenario(name: str, config: Config, inputs: List[Tuple[float, int, bool, bool]]):
    """Run a simulation scenario with given inputs."""
    print(f"\n{'='*60}")
    print(f"SCENARIO: {name}")
    print(f"{'='*60}")
    
    sim = EngineSimulator(config)
    
    for duration, pedal_pos, brake, start_cmd in inputs:
        steps = int(duration / config.dt)
        for _ in range(steps):
            sim.step(pedal_pos, brake, start_cmd)
    
    sim.save_log(f"{name.replace(' ', '_').lower()}.csv")
    sim.plot_results(f"{name.replace(' ', '_').lower()}.png")
    sim.print_summary()


def main():
    config = Config()
    
    # Scenario 1: Start + idle stabilization
    run_scenario(
        "1_Start_Idle_Stabilization",
        config,
        [
            (10.0, 1, False, True),  # Start and idle for 10 seconds
        ]
    )
    
    # Scenario 2: Pedal to 2, rpm rises, hold steady 5 sec, standard set, economy maintenance
    run_scenario(
        "2_Power_To_Economy",
        config,
        [
            (2.0, 1, False, True),   # Start and stabilize
            (3.0, 2, False, True),   # Pedal to 2, RPM rises
            (6.0, 2, False, True),   # Hold steady for 5+ seconds -> economy mode
            (5.0, 2, False, True),   # Continue in economy
        ]
    )
    
    # Scenario 3: Brake during economy -> back to default
    run_scenario(
        "3_Economy_Brake_Default",
        config,
        [
            (2.0, 1, False, True),   # Start
            (3.0, 2, False, True),   # Power mode
            (6.0, 2, False, True),   # Hold steady -> economy
            (3.0, 2, False, True),   # Economy maintenance
            (2.0, 2, True, True),    # Brake -> back to default idle
            (3.0, 1, False, True),   # Continue in default idle
        ]
    )
    
    # Scenario 4: Pedal jitter keeps Mode1 active
    run_scenario(
        "4_Pedal_Jitter_Mode1",
        config,
        [
            (2.0, 1, False, True),   # Start
            (2.0, 2, False, True),   # Pedal to 2
            (1.0, 1, False, True),   # Jitter: back to 1
            (2.0, 2, False, True),   # Back to 2
            (1.5, 1, False, True),   # Jitter again
            (3.0, 2, False, True),   # Back to 2 (never steady for 5 sec)
        ]
    )
    
    print("\n" + "="*60)
    print("ALL SCENARIOS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
