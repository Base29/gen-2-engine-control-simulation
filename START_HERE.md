# START HERE - Gen2 Engine Simulation Quick Start Guide

## 📚 DOCUMENTATION FILES

**Read these in order:**
1. **START_HERE.md** (this file) - How to run and find your results
2. **QUICK_REFERENCE.md** - One-page cheat sheet
3. **CYLINDER_GUIDE.md** - Understanding cylinder numbering
4. **SCENARIO_NOTES.md** - Detailed timeline for each scenario
5. **README.md** - Complete technical documentation

---

## STEP 1: RUN THE SIMULATION

Open your terminal and run:
```bash
python gen2_sim.py
```

The simulation will automatically run all 4 scenarios and create output files.

---

## STEP 2: FIND YOUR OUTPUT FILES

After running, you'll see these files in your folder:

### Scenario 1 Files (10 seconds - Idle Stabilization):
- `1_start_idle_stabilization.csv` - All the data
- `1_start_idle_stabilization.png` - Visual graph

### Scenario 2 Files (16 seconds - Power to Economy):
- `2_power_to_economy.csv` - All the data
- `2_power_to_economy.png` - Visual graph

### Scenario 3 Files (19 seconds - Brake Override):
- `3_economy_brake_default.csv` - All the data
- `3_economy_brake_default.png` - Visual graph

### Scenario 4 Files (11.5 seconds - Pedal Jitter):
- `4_pedal_jitter_mode1.csv` - All the data
- `4_pedal_jitter_mode1.png` - Visual graph

---

## STEP 3: OPEN THE GRAPHS

**Double-click any .png file** to see the visual results.

Each graph shows:
- **Top chart**: RPM over time (blue=actual, orange=filtered, red=target)
- **Bottom chart**: Which state the engine is in

---

## STEP 4: OPEN THE DATA IN EXCEL/SPREADSHEET

**Double-click any .csv file** to open in Excel or your spreadsheet program.

Each row is one timestep (0.01 seconds). You can see:
- Time
- State (OFF, DEFAULT_IDLE, MODE1_POWER, MODE2_ECONOMY)
- RPM values
- Which cylinder fired
- Targets

---

## WHAT EACH SCENARIO SHOWS

### SCENARIO 1: Start + Idle Stabilization (10 seconds)
**What happens:**
- Engine starts from 0 RPM
- Starter motor brings RPM up
- Engine stabilizes at idle (650 RPM target)
- Only 1 cylinder fires at idle
- Pulses fire when RPM drops below target

**Look for:**
- RPM rising from 0 to ~650
- Intermittent pulses to maintain idle
- Cylinder column shows which cylinder fires

---

### SCENARIO 2: Power to Economy Mode (16 seconds)
**What happens:**
- Starts at idle
- Pedal pressed to position 2 (acceleration)
- MODE1_POWER: All 4 cylinders fire in sequence (1→3→2→4)
- After 5 seconds steady: captures target RPM
- Switches to MODE2_ECONOMY
- Back to 1 cylinder for economy

**Look for:**
- RPM jump when pedal pressed
- Firing sequence changes from 1 cylinder to 4 cylinders
- State changes from DEFAULT_IDLE → MODE1_POWER → MODE2_ECONOMY
- Standard target gets set (check standard_target column)

---

### SCENARIO 3: Brake Interrupts Economy (19 seconds)
**What happens:**
- Same as Scenario 2 to get into economy mode
- Then brake is pressed
- Immediately exits economy mode
- Returns to default idle

**Look for:**
- Brake column changes to True
- State immediately changes to DEFAULT_IDLE
- Active target drops back to 650 RPM

---

### SCENARIO 4: Pedal Jitter (11.5 seconds)
**What happens:**
- Pedal keeps changing between position 1 and 2
- Never stays steady for 5 seconds
- Never enters economy mode
- Stays in power mode when pedal at 2

**Look for:**
- State bouncing between DEFAULT_IDLE and MODE1_POWER
- Never reaches MODE2_ECONOMY
- Pedal_pos column keeps changing

---

## UNDERSTANDING THE ENGINE BEHAVIOR

### At DEFAULT_IDLE:
- **Starter provides initial RPM** (simulated by pulses bringing RPM from 0)
- **1 cylinder involved** at idle
- Target: 650 RPM
- Fires pulse when RPM drops below (650 - 50) = 600 RPM

### In MODE1_POWER (Acceleration):
- **4 cylinders fire in sequence: 1 → 3 → 2 → 4**
- More frequent pulses
- Hysteresis-based control (uses RPM history)
- Raises RPM quickly

### In MODE2_ECONOMY:
- **1 cylinder for efficiency**
- **No cooldown restriction** (can fire as needed)
- Uses captured standard RPM target
- Intermittent pulses only

---

## QUICK TROUBLESHOOTING

**Problem: No files created**
- Check you're in the right folder
- Make sure Python ran without errors

**Problem: Can't open .png files**
- Try right-click → Open With → Preview (Mac) or Photos (Windows)

**Problem: Can't open .csv files**
- Try right-click → Open With → Excel or Numbers

**Problem: Want different idle RPM**
- Edit gen2_sim.py
- Find: `default_idle_rpm_min: float = 650.0`
- Change 650.0 to your desired RPM

---

## NEXT STEPS

1. Run the simulation: `python gen2_sim.py`
2. Open `1_start_idle_stabilization.png` to see the first scenario
3. Open `1_start_idle_stabilization.csv` in Excel to see all the data
4. Look at the other scenarios in order

---

## NEED HELP?

Check README.md for detailed explanations of:
- How the state machine works
- What each parameter does
- How to customize the simulation
- Technical details

---

**That's it! You're ready to explore the simulation results.**
