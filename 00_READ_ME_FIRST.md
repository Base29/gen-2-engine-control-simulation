# 📖 READ ME FIRST - Complete Guide to Gen2 Engine Simulation

## 🎯 ABSOLUTE BEGINNER? START HERE!

**Follow these 3 simple steps:**

1. **Open your terminal/command prompt**
2. **Type:** `python gen2_sim.py`
3. **Press Enter**

That's it! The simulation will run and create output files.

---

## 📚 ALL DOCUMENTATION FILES

Here are ALL the help files available. Read them in this order:

### 1️⃣ Getting Started (Read First)
- **00_READ_ME_FIRST.md** ← You are here!
- **START_HERE.md** - Step-by-step instructions for beginners
- **INDEX.md** - Navigation guide to all documentation

### 2️⃣ Quick Reference (Keep Handy)
- **QUICK_REFERENCE.md** - One-page cheat sheet with all key info
- **CYLINDER_GUIDE.md** - Understanding cylinder numbering (0-3 vs 1-4)
- **FLOWCHART.md** - Visual diagrams of how the engine works

### 3️⃣ Detailed Analysis (After Running)
- **SCENARIO_NOTES.md** - Second-by-second explanation of each scenario
- **README.md** - Complete technical documentation

### 4️⃣ Code
- **gen2_sim.py** - The actual simulation program

---

## 🚀 QUICK START (3 Steps)

### Step 1: Install Python (if needed)
```bash
# Check if you have Python:
python --version

# Should show Python 3.7 or higher
# If not, download from python.org
```

### Step 2: Install matplotlib
```bash
pip install matplotlib
```

### Step 3: Run the simulation
```bash
python gen2_sim.py
```

---

## 📊 WHAT YOU'LL GET

After running, you'll have **8 new files**:

### Data Files (CSV - open in Excel):
1. `1_start_idle_stabilization.csv`
2. `2_power_to_economy.csv`
3. `3_economy_brake_default.csv`
4. `4_pedal_jitter_mode1.csv`

### Graph Files (PNG - double-click to view):
1. `1_start_idle_stabilization.png`
2. `2_power_to_economy.png`
3. `3_economy_brake_default.png`
4. `4_pedal_jitter_mode1.png`

---

## 🎓 LEARNING PATH

### Path A: Visual Learner
1. Run the simulation
2. Open all 4 PNG files
3. Read **FLOWCHART.md**
4. Read **QUICK_REFERENCE.md**
5. Read **SCENARIO_NOTES.md**

### Path B: Data Analyst
1. Run the simulation
2. Open CSV files in Excel
3. Read **CYLINDER_GUIDE.md**
4. Read **SCENARIO_NOTES.md**
5. Read **README.md**

### Path C: Complete Understanding
1. Read **START_HERE.md**
2. Run the simulation
3. Read **QUICK_REFERENCE.md**
4. Read **CYLINDER_GUIDE.md**
5. Read **FLOWCHART.md**
6. Read **SCENARIO_NOTES.md**
7. Read **README.md**

---

## 🔑 KEY CONCEPTS (Must Know)

### The 4 States
1. **OFF** - Engine not running
2. **DEFAULT_IDLE** - Normal idle (650 RPM, 1 cylinder)
3. **MODE1_POWER** - Acceleration (4 cylinders, sequence 1→3→2→4)
4. **MODE2_ECONOMY** - Efficient cruising (1 cylinder, captured RPM)

### The 3 Inputs
1. **start_cmd** - Start the engine (True/False)
2. **pedal_pos** - Pedal position (1=idle, 2=power)
3. **brake** - Brake pedal (True/False)

### The Key Numbers
- **Idle RPM:** 650
- **Hysteresis:** 50 RPM
- **Pulse Gain:** 50 RPM per pulse
- **Steady Time:** 5 seconds to enter economy mode
- **Cylinders:** 4 total, but only 1 fires at idle

---

## 🎯 WHAT EACH SCENARIO SHOWS

### Scenario 1 (10 seconds)
**Start + Idle Stabilization**
- Engine starts from 0 RPM
- Stabilizes at 650 RPM
- Only 1 cylinder fires

### Scenario 2 (16 seconds)
**Power to Economy**
- Starts at idle
- Pedal pressed → 4 cylinders fire
- After 5 seconds steady → economy mode
- Back to 1 cylinder

### Scenario 3 (19 seconds)
**Brake Override**
- Same as Scenario 2
- Then brake pressed
- Immediately exits economy mode
- Safety override works

### Scenario 4 (11.5 seconds)
**Pedal Jitter**
- Pedal keeps changing
- Never steady for 5 seconds
- Never enters economy mode
- Shows robustness

---

## 🔍 HOW TO EXPLORE THE DATA

### In the PNG Graphs:
- **Top chart:** RPM over time (blue=actual, orange=filtered, red=target)
- **Bottom chart:** Which state the engine is in

### In the CSV Files:
- **time:** Seconds since start
- **state:** Current engine state
- **true_rpm:** Actual RPM
- **filtered_rpm:** Smoothed RPM (used for control)
- **cylinder:** Which cylinder fired (0-3 in code = 1-4 in real engine)
- **active_target:** Current RPM target

---

## ❓ COMMON QUESTIONS

**Q: Do I need to know programming?**
A: No! Just run the command and look at the graphs and CSV files.

**Q: What if I get an error?**
A: Check that Python and matplotlib are installed. Read START_HERE.md for help.

**Q: Why does the CSV show cylinder 0 instead of 1?**
A: Programming uses 0-indexing. Read CYLINDER_GUIDE.md for the full explanation.

**Q: Can I change the idle RPM?**
A: Yes! Edit gen2_sim.py and change `default_idle_rpm_min: float = 650.0`

**Q: What's the firing sequence?**
A: In power mode: Cylinders 1→3→2→4 (shown as 0→2→1→3 in CSV)

**Q: Why only 1 cylinder at idle?**
A: Efficiency! One cylinder is enough to maintain idle RPM and saves fuel.

---

## 🛠️ TROUBLESHOOTING

### Error: "python: command not found"
```bash
# Try:
python3 gen2_sim.py

# Or install Python from python.org
```

### Error: "No module named 'matplotlib'"
```bash
pip install matplotlib

# Or try:
pip3 install matplotlib
```

### Error: "Permission denied"
```bash
# Make sure you're in the right directory
# Check you have write permissions
```

### No output files created
- Check for error messages in the terminal
- Make sure the simulation completed
- Check you're in the correct directory

---

## 📞 NEED MORE HELP?

### For Basic Usage:
→ Read **START_HERE.md**

### For Understanding Results:
→ Read **SCENARIO_NOTES.md**

### For Technical Details:
→ Read **README.md**

### For Visual Understanding:
→ Read **FLOWCHART.md**

### For Cylinder Confusion:
→ Read **CYLINDER_GUIDE.md**

### For Quick Lookup:
→ Read **QUICK_REFERENCE.md**

---

## 🎉 YOU'RE READY!

**Next step:** Open **START_HERE.md** and follow the instructions!

Or just run this command right now:
```bash
python gen2_sim.py
```

Then open the PNG files to see your results!

---

## 📋 FILE CHECKLIST

After running, you should have these files:

**Documentation (already there):**
- [ ] 00_READ_ME_FIRST.md (this file)
- [ ] START_HERE.md
- [ ] INDEX.md
- [ ] QUICK_REFERENCE.md
- [ ] CYLINDER_GUIDE.md
- [ ] FLOWCHART.md
- [ ] SCENARIO_NOTES.md
- [ ] README.md
- [ ] gen2_sim.py

**Output (created after running):**
- [ ] 1_start_idle_stabilization.csv
- [ ] 1_start_idle_stabilization.png
- [ ] 2_power_to_economy.csv
- [ ] 2_power_to_economy.png
- [ ] 3_economy_brake_default.csv
- [ ] 3_economy_brake_default.png
- [ ] 4_pedal_jitter_mode1.csv
- [ ] 4_pedal_jitter_mode1.png

---

**Good luck, Paul! You've got this! 🚀**
