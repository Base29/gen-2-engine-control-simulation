# Gen2 Engine Simulation - Documentation Index

## 🎯 START HERE

**New user? Follow this path:**

1. Read **START_HERE.md** first
2. Run `python gen2_sim.py`
3. Open the PNG files to see graphs
4. Read **SCENARIO_NOTES.md** to understand what happened
5. Open CSV files in Excel to explore the data

---

## 📖 Documentation Files

### For Beginners

| File | Purpose | When to Read |
|------|---------|--------------|
| **START_HERE.md** | Step-by-step instructions | Read first |
| **QUICK_REFERENCE.md** | One-page cheat sheet | Keep handy while analyzing |
| **CYLINDER_GUIDE.md** | Cylinder numbering explained | When confused about cylinder numbers |

### For Detailed Analysis

| File | Purpose | When to Read |
|------|---------|--------------|
| **SCENARIO_NOTES.md** | Timeline and details for each scenario | After running simulation |
| **README.md** | Complete technical documentation | For deep understanding |

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install matplotlib

# Run simulation
python gen2_sim.py

# Output files created:
# - 4 CSV files (data)
# - 4 PNG files (graphs)
```

---

## 📊 Output Files

After running, you'll have these files:

### Scenario 1: Start + Idle (10 seconds)
- `1_start_idle_stabilization.csv` - Data
- `1_start_idle_stabilization.png` - Graph

### Scenario 2: Power to Economy (16 seconds)
- `2_power_to_economy.csv` - Data
- `2_power_to_economy.png` - Graph

### Scenario 3: Brake Override (19 seconds)
- `3_economy_brake_default.csv` - Data
- `3_economy_brake_default.png` - Graph

### Scenario 4: Pedal Jitter (11.5 seconds)
- `4_pedal_jitter_mode1.csv` - Data
- `4_pedal_jitter_mode1.png` - Graph

---

## 🔍 What Each File Teaches You

### START_HERE.md
- How to run the simulation
- Where to find output files
- How to open graphs and data
- Basic understanding of each scenario

### QUICK_REFERENCE.md
- Engine specifications (650 RPM idle, 4 cylinders)
- State transition diagram
- CSV column meanings
- Key behaviors in each mode
- Common questions answered

### CYLINDER_GUIDE.md
- Why CSV shows 0-3 instead of 1-4
- Firing sequence: 1→3→2→4 (real) = 0→2→1→3 (CSV)
- Why only 1 cylinder at idle
- How to verify correct operation

### SCENARIO_NOTES.md
- Second-by-second timeline for each scenario
- What to look for in the CSV data
- Expected behavior at each phase
- How to verify correct operation
- Troubleshooting data issues

### README.md
- Complete technical documentation
- Configuration parameters explained
- State machine logic
- RPM physics model
- Hall sensor simulation
- How to customize the simulation
- Performance characteristics

---

## 🎓 Learning Path

### Level 1: Basic Understanding
1. Read START_HERE.md
2. Run the simulation
3. Look at the PNG graphs
4. Read QUICK_REFERENCE.md

### Level 2: Data Analysis
1. Open CSV files in Excel
2. Read CYLINDER_GUIDE.md
3. Read SCENARIO_NOTES.md
4. Verify behaviors described in notes

### Level 3: Deep Dive
1. Read README.md completely
2. Understand state machine logic
3. Understand RPM physics
4. Modify configuration parameters
5. Create custom scenarios

---

## 🔧 Key Concepts

### Engine Modes

**DEFAULT_IDLE**
- After engine start
- Pedal position 1
- 650 RPM target
- 1 cylinder (cylinder 0)
- Intermittent pulses

**MODE1_POWER**
- Pedal position 2
- Acceleration mode
- 4 cylinders firing
- Sequence: 0→2→1→3
- Frequent pulses

**MODE2_ECONOMY**
- After 5 seconds steady pedal
- Efficiency mode
- 1 cylinder (cylinder 0)
- Uses captured RPM target
- No cooldown restriction

### Important Numbers

| Parameter | Value |
|-----------|-------|
| Idle RPM | 650 |
| Hysteresis | 50 RPM |
| Pulse Gain | 50 RPM |
| Cooldown | 0.1 seconds |
| Steady Time | 5 seconds |
| Cylinders | 4 |

---

## ❓ Common Questions

**Q: Where do I start?**
A: Read START_HERE.md, then run `python gen2_sim.py`

**Q: How do I see the results?**
A: Double-click the PNG files for graphs, open CSV files in Excel for data

**Q: Why does the CSV show cylinder 0 instead of 1?**
A: Programming uses 0-indexing. Read CYLINDER_GUIDE.md for details.

**Q: What's the firing sequence?**
A: Real engine: 1→3→2→4. In CSV: 0→2→1→3. Same thing, different numbering.

**Q: Why only 1 cylinder at idle?**
A: Efficiency. One cylinder is enough to maintain idle RPM.

**Q: How do I change the idle RPM?**
A: Edit gen2_sim.py, find `default_idle_rpm_min: float = 650.0`, change the value.

**Q: What does hysteresis mean?**
A: It's a buffer. Pulse fires when RPM drops 50 below target, preventing constant firing.

**Q: Why doesn't economy mode use cooldown?**
A: To allow responsive control while maintaining efficiency.

**Q: How is the standard RPM target set?**
A: Captured from filtered_rpm when pedal is steady for 5 seconds in power mode.

**Q: What resets the steady timer?**
A: Any change in pedal position.

---

## 🛠️ Troubleshooting

**Problem: Python not found**
```bash
# Install Python 3.7 or higher
# Then try again
```

**Problem: matplotlib not found**
```bash
pip install matplotlib
```

**Problem: No output files**
- Check you're in the right directory
- Check for error messages
- Ensure you have write permissions

**Problem: Can't open PNG files**
- Right-click → Open With → Preview (Mac) or Photos (Windows)

**Problem: Can't open CSV files**
- Right-click → Open With → Excel or Numbers

**Problem: Simulation runs but results look wrong**
- Check SCENARIO_NOTES.md for expected behavior
- Verify configuration in gen2_sim.py
- Check console output for errors

---

## 📞 Getting Help

1. Check the relevant documentation file
2. Read SCENARIO_NOTES.md for expected behavior
3. Verify your configuration matches the defaults
4. Check that output files were created
5. Look at console output for error messages

---

## 🎯 Quick Navigation

- **Just want to run it?** → START_HERE.md
- **Need a cheat sheet?** → QUICK_REFERENCE.md
- **Confused about cylinders?** → CYLINDER_GUIDE.md
- **Want detailed analysis?** → SCENARIO_NOTES.md
- **Need technical details?** → README.md
- **Want to customize?** → README.md (Configuration section)

---

**Ready to begin? Open START_HERE.md and follow the steps!**
