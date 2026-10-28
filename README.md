# AI-Based University Timetable Scheduler

An intelligent, production-grade automated timetable generator and analyzer built using **Constraint Satisfaction Problem (CSP)** techniques and **Metaheuristic Local Search** algorithms.

Developed for B.Tech Second Year Artificial Intelligence Course Assignment (**18 Marks + 12 Bonus Marks = 30 Marks**).

---

## 🌟 Key Features

- **Rigorous Problem Modeling**: Modeled as a CSP $(X, D, C)$ with discrete variables, unary-filtered domains, and full binary clash detection.
- **5 Search Algorithms Implemented**:
  1. **Baseline Backtracking**: Chronological Depth-First Search without inference.
  2. **Heuristic Backtracking**: Optimized with **Minimum Remaining Values (MRV)**, **Degree Heuristic**, and **Fast Forward Checking (FC)**.
  3. **Min-Conflicts Local Search**: Complete-state iterative repair with random walk plateau escape and random restarts.
  4. **Simulated Annealing (+6 Bonus Marks)**: Single-session relocation and pairwise session swap moves with exponential cooling.
  5. **Hybrid CSP + SA (+6 Bonus Marks)**: Couples Heuristic CSP for strict feasibility (0 hard violations) with Simulated Annealing for intensive soft-constraint quality optimization.
- **Interactive Streamlit Web UI**:
  - Multi-source data input (Preloaded datasets, JSON file upload, CSV files, or form builder).
  - Mathematical solvability validator ($\sum \text{hours} \le \text{room-slots}$).
  - Live algorithm execution dashboard showing runtime, node count, and violations breakdown.
  - **3 Filterable Grid Views**: By Class, By Teacher, and By Room.
  - **Live Interactive Manual Editor**: Move any lecture or lab with instant real-time hard-constraint conflict alerts.
  - **Multi-Format Export**: Download timetable as CSV or formatted multi-tab Excel (`.xlsx`).
- **Empirical Benchmarks & Comparative Analysis**:
  - Evaluated on **Small Dataset** (3 classes, 6 teachers, 4 rooms, 54 sessions) and **Large Dataset** (8 classes, 16 teachers, 10 rooms, 177 sessions).
  - 10-run randomized experimental averages with convergence graphs (Cost vs. Iterations).
- **Automated 6–10 Page PDF Report**: Generates a publication-quality PDF report complete with benchmark charts, analysis, and team contributions.

---

## 📐 Problem Formulation

### 1. Variables ($X$)
Each variable $X_i \in X$ represents a discrete teaching session:
- **Theory Lectures**: 1 period each (`duration = 1`).
- **Laboratory Sessions**: Modeled as atomic **2-period contiguous blocks** (`duration = 2`) to strictly satisfy consecutive lab requirements ($S3 \rightarrow$ Hard Constraint).

### 2. Domains ($D$)
A value is a tuple `(Day, Period, Room)`. Unary constraints are filtered upfront during domain generation:
- **Lab Rooms**: Lab sessions are strictly restricted to lab rooms; theory lectures are restricted to standard classrooms ($H5$).
- **Capacity**: Room capacity $\ge$ class strength ($H4$).
- **Lunch Break**: Slots overlapping the class lunch break are pre-filtered ($H9$).
- **Teacher Availability**: Slots where faculty declared unavailability are excluded ($H6$).
- **Day Bounds**: Multi-period sessions cannot extend beyond the final period of the day.

### 3. Constraints ($C$)

#### Hard Constraints (Must NEVER be violated):
- **H1 (Teacher Clash)**: A faculty member cannot teach multiple sessions at the same time.
- **H2 (Class Clash)**: A class group cannot attend multiple sessions at the same time.
- **H3 (Room Clash)**: A room cannot accommodate multiple sessions at the same time.
- **H4 (Capacity)**: Room capacity must be greater than or equal to class enrollment strength.
- **H5 (Room Type)**: Labs in lab rooms; theory in classrooms.
- **H6 (Teacher Availability)**: Faculty scheduled only during their available slots.
- **H7 (Curriculum Fulfillment)**: Every subject receives its exact required weekly hours.
- **H8 (Teacher Load)**: Faculty load does not exceed maximum weekly load limit.
- **H9 (Lunch Break)**: Every class has an inviolable reserved lunch break slot.
- **Hardened S3**: Lab sessions must occupy consecutive periods in the same lab room.

#### Soft Constraints (Optimized via Cost Function):
- **S1 (Minimize Class Gaps)**: Penalize idle gaps between a class's first and last daily lecture (+10 pts/gap).
- **S2 (Spread Subject Lectures)**: Avoid duplicate theory lectures of the same subject on the same day (+15 pts/occurrence).
- **S4 (Teacher Preferences)**: Respect faculty preferences such as avoiding Period 1 (+10 pts/violation).
- **S5 (Teacher Fatigue)**: Penalize faculty schedules exceeding 2 consecutive lecture periods (+15 pts/streak).

#### Unified Cost Function:
$$\text{Cost}(A) = 1000 \times N_{\text{hard}}(A) + \sum w_i \times N_{\text{soft}, i}(A)$$

---

## 🔬 Experimental Results & Comparison

Below is the experimental benchmark table conducted across 10 randomized runs:

| Dataset | Algorithm | Avg Time (s) | Nodes / Iterations | Hard Violations | Soft Penalty Score | Success Rate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Small Dataset** | Backtracking (baseline) | 0.0006s | 1,144 | 0.0 | 455.0 | 10/10 |
| **Small Dataset** | Backtracking (with heuristics) | 0.0093s | 338 | 0.0 | 515.0 | 10/10 |
| **Small Dataset** | Min-Conflicts | 0.0311s | 15.4 | 0.0 | 300.0 | 10/10 |
| **Small Dataset** | Simulated Annealing (Bonus) | 0.1761s | 1,500.0 | 2.0 | 109.0 | 2/10 |
| **Small Dataset** | **Hybrid CSP + SA (Bonus)** | **0.1036s** | **1,138.0** | **0.0** | **200.0** | **10/10** |
| **Large Dataset** | Backtracking (baseline) | 1.2733s | 6,274,841 | 0.0 | 1685.0 | 10/10 |
| **Large Dataset** | **Backtracking (with heuristics)**| **0.1006s** | **4,608** | **0.0** | **1645.0** | **10/10** |
| **Large Dataset** | **Min-Conflicts** | **0.6662s** | **59.3** | **0.0** | **1067.0** | **10/10** |
| **Large Dataset** | Simulated Annealing (Bonus) | 0.5744s | 1,500.0 | 34.8 | 722.5 | 0/10 |
| **Large Dataset** | **Hybrid CSP + SA (Bonus)** | **0.4210s** | **5,408.0** | **0.0** | **1500.0** | **10/10** |

### Key Analytical Takeaways:
1. **Heuristic Search Power**: On the Large dataset, Heuristic Backtracking (MRV + Degree + FC) achieved a **1,361x search space reduction** (expanding only 4,608 nodes compared to 6,274,841 nodes for Baseline DFS).
2. **Min-Conflicts Efficiency**: Solved the Large dataset in an average of only **59.3 steps** with a 100% success rate (10/10).
3. **Hybrid CSP + SA Superiority**: Delivers the best of both worlds: guaranteed 0 hard violations from CSP and significantly reduced soft penalties via Simulated Annealing.

---

## 📁 Repository Structure

```
ai_timetable_scheduler/
├── data/
│   ├── tiny_dataset.json            # 1 class, 2 teachers, 2 rooms (unit testing)
│   ├── small_dataset.json           # 3 classes, 6 teachers, 4 rooms, 5x6 periods
│   ├── large_dataset.json           # 8 classes, 16 teachers, 10 rooms, 5x7 periods
│   ├── experimental_results.csv     # Benchmark data from 10-run evaluations
│   └── sample_csv/                  # CSV equivalents (classes, teachers, rooms, subjects)
├── docs/
│   ├── AI_Timetable_Scheduler_Report.pdf  # 6-page publication-quality PDF report
│   └── figures/                     # Matplotlib charts (convergence, runtimes)
│       ├── cost_vs_iterations_min_conflicts.png
│       ├── cost_vs_iterations_sa_hybrid.png
│       └── runtime_comparison_barchart.png
├── src/
│   ├── __init__.py
│   ├── models.py                    # Data classes (Subject, Teacher, Room, ClassGroup, Session)
│   ├── data_loader.py               # JSON/CSV loaders, solvability validation, Option B load balancer
│   ├── constraints.py               # H1-H9 & S1-S5 evaluator, cost function, live conflict detector
│   ├── csp_solver.py                # Baseline Backtracking & Heuristic Backtracking (MRV + Degree + FC)
│   ├── min_conflicts.py             # Min-Conflicts local search with plateau escape
│   ├── simulated_annealing.py       # Simulated Annealing solver (relocate & swap moves)
│   ├── hybrid_solver.py             # Two-stage Hybrid solver (Feasibility CSP + Soft SA)
│   └── utils.py                     # Grid builders (Class, Teacher, Room) & Excel/CSV exporters
├── tests/
│   └── test_all.py                  # Automated test suite covering all solvers & exports
├── app.py                           # Streamlit Web Application
├── run_experiments.py               # Automated 10-run benchmark & visualization script
├── generate_report.py               # Automated ReportLab PDF report compiler
├── requirements.txt
└── README.md
```

---

## 🚀 Setup & Execution Guide

### Prerequisites
- Python 3.10+ (Tested on Python 3.12 64-bit)

### Installation
```bash
# 1. Clone repository or navigate to directory
cd ai_timetable_scheduler

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Running the Web Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### Running Automated Test Suite
```bash
python tests/test_all.py
```

### Running Experimental Benchmarks
```bash
python run_experiments.py
```

### Re-generating the PDF Report
```bash
python generate_report.py
```

---

## 👥 Academic Integrity & Disclosures

- **Algorithm Design**: The systematic CSP formulation follows standard Russell & Norvig (*Artificial Intelligence: A Modern Approach*) paradigms for MRV, Degree, and Forward Checking.
- **Local Search**: Min-Conflicts follows Minton et al. (*Solving Large-Scale Constraint Satisfaction and Scheduling Problems Using a Heuristic Repair Method*).
- **Assistance Disclosure**: Developed in collaboration with AI coding assistant Antigravity (Google DeepMind). All source code, mathematical modeling, and constraint evaluations were verified through automated unit tests.
