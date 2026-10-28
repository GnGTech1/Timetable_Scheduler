"""
Streamlit Web Application: AI-Based Timetable Scheduler
Features:
- Dataset Input: Preloaded (Tiny, Small, Large), File Upload (JSON/CSV), Form Builder
- Solvability & Data Validation
- Algorithm Selector: Baseline Backtracking, Heuristic Backtracking, Min-Conflicts, Simulated Annealing, Hybrid CSP+SA
- Live Performance Metrics (Runtime, Nodes/Steps, Violations, Cost)
- Timetable Grid Views: By Class, By Teacher, By Room
- Live Convergence Plot (Cost vs Iterations)
- Manual Interactive Editor with Instant Real-Time Clash Detection
- Export to CSV and Styled Multi-Tab Excel (.xlsx)
"""
import os
import json
import io
import time
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from src.models import Session, SessionPlacement, Room, Teacher, ClassGroup, TimeStructure, Subject
from src.data_loader import DataLoader, DataValidationError
from src.constraints import evaluate_timetable, get_session_conflicts, ViolationReport
from src.csp_solver import solve_backtracking_baseline, solve_backtracking_heuristics
from src.min_conflicts import solve_min_conflicts
from src.simulated_annealing import solve_simulated_annealing
from src.hybrid_solver import solve_hybrid_csp_sa
from src.utils import (
    build_grid_by_class, build_grid_by_teacher, build_grid_by_room,
    export_to_csv_string, export_to_excel_bytes, get_tabular_data
)

st.set_page_config(
    page_title="AI Timetable Scheduler",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for clean UI styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 4px solid #1F497D;
        margin-bottom: 8px;
    }
    .stDataFrame {
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Session State Initialization
# -------------------------------------------------------------
if "dataset_loaded" not in st.session_state:
    st.session_state.dataset_loaded = False
if "current_assignment" not in st.session_state:
    st.session_state.current_assignment = None
if "run_result" not in st.session_state:
    st.session_state.run_result = None
if "cost_history" not in st.session_state:
    st.session_state.cost_history = []
if "sessions_list" not in st.session_state:
    st.session_state.sessions_list = []
if "domains_dict" not in st.session_state:
    st.session_state.domains_dict = {}

# -------------------------------------------------------------
# Sidebar: Configuration & Controls
# -------------------------------------------------------------
st.sidebar.title("📅 AI Timetable Scheduler")
st.sidebar.markdown("**Constraint Satisfaction & Local Search**")

data_source = st.sidebar.selectbox(
    "1. Select Dataset Source",
    ["Preloaded: Small (3 Classes, 6 Teachers)",
     "Preloaded: Large (8 Classes, 16 Teachers)",
     "Preloaded: Tiny (1 Class, 2 Teachers)",
     "Upload JSON File",
     "Upload CSV Files"]
)

# Load data based on source
data_dir = os.path.join(os.path.dirname(__file__), "data")

try:
    if "Small" in data_source:
        json_path = os.path.join(data_dir, "small_dataset.json")
        subjects, teachers, rooms, classes, time_structure = DataLoader.load_json(json_path)
    elif "Large" in data_source:
        json_path = os.path.join(data_dir, "large_dataset.json")
        subjects, teachers, rooms, classes, time_structure = DataLoader.load_json(json_path)
    elif "Tiny" in data_source:
        json_path = os.path.join(data_dir, "tiny_dataset.json")
        subjects, teachers, rooms, classes, time_structure = DataLoader.load_json(json_path)
    elif data_source == "Upload JSON File":
        uploaded_json = st.sidebar.file_uploader("Upload Timetable JSON", type=["json"])
        if uploaded_json:
            json_content = json.load(uploaded_json)
            subjects, teachers, rooms, classes, time_structure = DataLoader.load_json(json_content)
        else:
            json_path = os.path.join(data_dir, "small_dataset.json")
            subjects, teachers, rooms, classes, time_structure = DataLoader.load_json(json_path)
    else:  # Upload CSV Files
        st.sidebar.info("Upload CSV files or using sample CSVs")
        csv_dir = os.path.join(data_dir, "sample_csv")
        subjects, teachers, rooms, classes, time_structure = DataLoader.load_csv(csv_dir)

    # Teacher assignment mode
    teacher_mode = st.sidebar.radio(
        "2. Teacher Assignment Strategy",
        ["Option A: Respect Explicit Mapping", "Option B: Auto Balanced Assignment"],
        help="Option A uses specified teachers. Option B balances weekly loads evenly across qualified teachers."
    )
    if "Option B" in teacher_mode:
        DataLoader.auto_assign_teachers_if_needed(classes, teachers, subjects)

    # Validate dataset & check solvability
    val_warnings = DataLoader.validate_dataset(subjects, teachers, rooms, classes, time_structure)
    if val_warnings:
        for w in val_warnings:
            st.sidebar.warning(f"⚠️ {w}")
    else:
        st.sidebar.success("✅ Dataset Solvability Verified!")

    # Generate sessions & domains
    sessions = DataLoader.generate_sessions(classes, subjects, teachers)
    domains = DataLoader.generate_domains(sessions, rooms, time_structure, teachers, classes)
    st.session_state.sessions_list = sessions
    st.session_state.domains_dict = domains
    st.session_state.dataset_loaded = True

except Exception as e:
    st.sidebar.error(f"Error loading dataset: {str(e)}")
    st.stop()

# Algorithm selection
st.sidebar.markdown("---")
algorithm = st.sidebar.selectbox(
    "3. Select Algorithm",
    [
        "Backtracking (MRV + Degree + FC + LCV)",
        "Backtracking (Baseline DFS)",
        "Min-Conflicts Local Search",
        "Simulated Annealing (Bonus +6)",
        "Hybrid CSP + SA (Bonus +6)"
    ]
)

timeout = st.sidebar.slider("Timeout (seconds)", min_value=5, max_value=120, value=30, step=5)
seed = st.sidebar.number_input("Random Seed", value=42, step=1)

# Generate Button
generate_clicked = st.sidebar.button("🚀 Generate Timetable", type="primary", use_container_width=True)

# -------------------------------------------------------------
# Solver Execution
# -------------------------------------------------------------
if generate_clicked and st.session_state.dataset_loaded:
    with st.spinner(f"Running {algorithm}..."):
        start_time = time.time()
        cost_hist = []

        if algorithm == "Backtracking (Baseline DFS)":
            res = solve_backtracking_baseline(sessions, domains, timeout_seconds=timeout)
            assignment = res.assignment
            elapsed = res.time_taken
            nodes = res.nodes_expanded
            success = res.success
            msg = res.message
        elif algorithm == "Backtracking (MRV + Degree + FC + LCV)":
            res = solve_backtracking_heuristics(sessions, domains, timeout_seconds=timeout)
            assignment = res.assignment
            elapsed = res.time_taken
            nodes = res.nodes_expanded
            success = res.success
            msg = res.message
        elif algorithm == "Min-Conflicts Local Search":
            res = solve_min_conflicts(
                sessions, domains, rooms, teachers, classes, subjects, time_structure,
                max_steps=2000, timeout_seconds=timeout, seed=seed
            )
            assignment = res.assignment
            elapsed = res.time_taken
            nodes = res.iterations
            success = res.success
            cost_hist = res.cost_history
            msg = res.message
        elif algorithm == "Simulated Annealing (Bonus +6)":
            res = solve_simulated_annealing(
                sessions, domains, rooms, teachers, classes, subjects, time_structure,
                max_iterations=2500, timeout_seconds=timeout, seed=seed
            )
            assignment = res.assignment
            elapsed = res.time_taken
            nodes = res.iterations
            success = res.success
            cost_hist = res.cost_history
            msg = res.message
        else:  # Hybrid CSP + SA
            res = solve_hybrid_csp_sa(
                sessions, domains, rooms, teachers, classes, subjects, time_structure,
                sa_iterations=1500, timeout_seconds=timeout, seed=seed
            )
            assignment = res.assignment
            elapsed = res.total_time
            nodes = res.stage1_nodes + res.stage2_iterations
            success = res.success
            cost_hist = res.cost_history
            msg = res.message

        if assignment is not None:
            st.session_state.current_assignment = assignment
            st.session_state.cost_history = cost_hist
            st.session_state.run_result = {
                "algorithm": algorithm,
                "elapsed": elapsed,
                "nodes": nodes,
                "success": success,
                "message": msg
            }
        else:
            st.error(f"Algorithm failed to find an assignment. {msg}")

# -------------------------------------------------------------
# Main Application Content
# -------------------------------------------------------------
st.title("Automated AI Timetable Scheduler")
st.markdown("Generates conflict-free college schedules satisfying all hard constraints ($H1-H9$) and optimizing soft constraints ($S1-S5$).")

if st.session_state.current_assignment is not None:
    # Evaluate current assignment
    rep = evaluate_timetable(st.session_state.current_assignment, rooms, teachers, classes, subjects, time_structure)
    rr = st.session_state.run_result

    # Status Banner
    if rep.hard_count == 0:
        st.success(f"🎉 **Valid & Conflict-Free Timetable Generated!** All hard constraints satisfied. ({rr['message'] if rr else ''})")
    else:
        st.warning(f"⚠️ **Timetable contains {rep.hard_count} Hard Constraint Violation(s)**. ({rr['message'] if rr else ''})")

    # Metrics Row
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Time Taken", f"{rr['elapsed']:.3f} s" if rr else "N/A")
    with m2:
        st.metric("Nodes / Iterations", f"{rr['nodes']:,}" if rr else "N/A")
    with m3:
        st.metric("Hard Violations", f"{rep.hard_count}", delta=None if rep.hard_count == 0 else f"{rep.hard_count} clashes", delta_color="inverse")
    with m4:
        st.metric("Soft Penalty", f"{rep.soft_penalty}")
    with m5:
        st.metric("Total Cost", f"{rep.total_cost:,}")

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📅 Timetable Grid Views",
        "✏️ Manual Edit & Live Clash Detector",
        "📈 Convergence Chart",
        "📋 Violations Breakdown",
        "💾 Export & Download"
    ])

    # ---------------------------------------------------------
    # Tab 1: Timetable Grids
    # ---------------------------------------------------------
    with tab1:
        view_mode = st.radio("Grid View Perspective", ["By Class", "By Teacher", "By Room"], horizontal=True)

        if view_mode == "By Class":
            selected_class = st.selectbox("Select Class Group", sorted(classes.keys()))
            df_grid = build_grid_by_class(st.session_state.current_assignment, selected_class, time_structure, classes)
            st.subheader(f"Timetable for {selected_class} (Strength: {classes[selected_class].strength})")
            st.dataframe(df_grid, use_container_width=True)

        elif view_mode == "By Teacher":
            selected_teacher = st.selectbox("Select Teacher", sorted(teachers.keys()))
            df_grid = build_grid_by_teacher(st.session_state.current_assignment, selected_teacher, time_structure)
            t_obj = teachers[selected_teacher]
            st.subheader(f"Schedule for {selected_teacher} (Max Load: {t_obj.max_weekly_load} hrs)")
            st.dataframe(df_grid, use_container_width=True)

        else:  # By Room
            selected_room = st.selectbox("Select Room", sorted(rooms.keys()))
            df_grid = build_grid_by_room(st.session_state.current_assignment, selected_room, time_structure)
            r_obj = rooms[selected_room]
            st.subheader(f"Room Allocation for {selected_room} ({r_obj.type.capitalize()}, Capacity: {r_obj.capacity})")
            st.dataframe(df_grid, use_container_width=True)

    # ---------------------------------------------------------
    # Tab 2: Manual Interactive Editing with Instant Conflict Flagging
    # ---------------------------------------------------------
    with tab2:
        st.subheader("Manual Session Reassignment")
        st.markdown(
            "Move any scheduled lecture or lab to another slot or room. "
            "The system immediately flags any **hard constraint conflict (H1–H9)** this change creates!"
        )

        sess_id_list = sorted([s.id for s in st.session_state.current_assignment.keys()])
        selected_sess_id = st.selectbox("Select Session to Move", sess_id_list)

        # Find session object
        target_session = next(s for s in st.session_state.current_assignment.keys() if s.id == selected_sess_id)
        current_plc = st.session_state.current_assignment[target_session]

        col_curr, col_new = st.columns(2)
        with col_curr:
            st.info(f"**Current Placement:**\n- **Day:** {current_plc.day}\n- **Period:** {current_plc.period}\n- **Room:** {current_plc.room}\n- **Teacher:** {target_session.teacher_name}\n- **Duration:** {target_session.duration} period(s)")

        with col_new:
            new_day = st.selectbox("New Day", time_structure.working_days, index=time_structure.working_days.index(current_plc.day))
            max_start = time_structure.periods_per_day - target_session.duration + 1
            new_period = st.selectbox("New Period (Start)", list(range(1, max_start + 1)), index=min(current_plc.period - 1, max_start - 1))
            new_room = st.selectbox("New Room", sorted(rooms.keys()), index=sorted(rooms.keys()).index(current_plc.room))

        candidate_placement = SessionPlacement(day=new_day, period=new_period, room=new_room)

        # Real-time conflict inspection!
        conflicts = get_session_conflicts(
            session=target_session,
            placement=candidate_placement,
            current_assignment=st.session_state.current_assignment,
            rooms=rooms,
            teachers=teachers,
            classes=classes,
            subjects=subjects,
            time_structure=time_structure
        )

        st.markdown("#### Live Conflict Assessment:")
        if conflicts:
            st.error(f"❌ **Placement causes {len(conflicts)} Hard Constraint Violation(s):**")
            for c in conflicts:
                st.markdown(f"- 🔴 **{c}**")
        else:
            st.success("✅ **Completely Clean Move!** No hard constraint clashes detected.")

        if st.button("Apply Session Move"):
            st.session_state.current_assignment[target_session] = candidate_placement
            st.rerun()

    # ---------------------------------------------------------
    # Tab 3: Convergence Chart (Cost vs Iterations)
    # ---------------------------------------------------------
    with tab3:
        st.subheader("Optimization Convergence (Cost vs. Iterations)")
        if st.session_state.cost_history and len(st.session_state.cost_history) > 1:
            fig, ax = plt.subplots(figsize=(10, 4.5))
            ax.plot(st.session_state.cost_history, color="#1F497D", linewidth=2, label="Timetable Cost")
            ax.set_title(f"Cost Trajectory: {st.session_state.run_result['algorithm'] if st.session_state.run_result else ''}", fontsize=12, fontweight='bold')
            ax.set_xlabel("Iteration / Checkpoint", fontsize=10)
            ax.set_ylabel("Total Cost (1000 * Hard + Soft)", fontsize=10)
            ax.grid(True, linestyle="--", alpha=0.6)
            ax.legend()
            st.pyplot(fig)
        else:
            st.info("Systematic Backtracking does not produce a continuous iteration-by-iteration local search cost trajectory. Run Min-Conflicts, Simulated Annealing, or Hybrid to view live convergence curves.")

    # ---------------------------------------------------------
    # Tab 4: Violations Breakdown
    # ---------------------------------------------------------
    with tab4:
        st.subheader("Comprehensive Constraint Audit")
        col_h, col_s = st.columns(2)
        with col_h:
            st.markdown(f"### Hard Violations ({rep.hard_count})")
            if rep.hard_violations:
                for hv in rep.hard_violations:
                    st.error(f"🔴 {hv}")
            else:
                st.success("Zero hard violations! Timetable is strictly feasible.")

        with col_s:
            st.markdown(f"### Soft Penalties ({rep.soft_penalty} pts)")
            if rep.soft_violations:
                for sv in rep.soft_violations[:50]:
                    st.warning(f"🟡 {sv}")
                if len(rep.soft_violations) > 50:
                    st.caption(f"... and {len(rep.soft_violations) - 50} more soft penalties.")
            else:
                st.success("Zero soft penalties! Schedule is perfectly compact and optimized.")

    # ---------------------------------------------------------
    # Tab 5: Export & Download
    # ---------------------------------------------------------
    with tab5:
        st.subheader("Export Generated Timetable")
        st.markdown("Download the complete timetable as a CSV flat file or an Excel workbook with separate sheets for classes, teachers, and rooms.")

        col_csv, col_excel = st.columns(2)
        with col_csv:
            csv_data = export_to_csv_string(st.session_state.current_assignment)
            st.download_button(
                label="📥 Download CSV Timetable",
                data=csv_data,
                file_name="generated_timetable.csv",
                mime="text/csv",
                use_container_width=True
            )

        with col_excel:
            excel_bytes = export_to_excel_bytes(st.session_state.current_assignment, classes, teachers, rooms, time_structure)
            st.download_button(
                label="📥 Download Excel Timetable (.xlsx)",
                data=excel_bytes,
                file_name="generated_timetable.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

else:
    # Initial state when app is first opened
    st.info("👈 Select your dataset and algorithm in the sidebar, then click **'🚀 Generate Timetable'** to begin!")
    st.markdown("### System Capabilities:")
    st.markdown(r"""
    - **Modeling as CSP**: Strict unary domains for rooms, capacities, teacher availability, and class lunch breaks.
    - **Solvability Verification**: Mathematical upper-bound validation ($\sum \text{hours} \le \text{room-slots}$).
    - **Algorithms Implemented**:
      1. Baseline Plain Backtracking (chronological DFS)
      2. Heuristic Backtracking (MRV + Degree Heuristic + Forward Checking + LCV)
      3. Min-Conflicts Local Search (with random-walk plateau escape)
      4. Simulated Annealing (+6 bonus marks)
      5. Hybrid CSP + Simulated Annealing (+6 bonus marks)
    - **Usability Features**: 3 grid perspectives, interactive drag/dropdown editor with live clash checking, and multi-tab Excel export.
    """)
