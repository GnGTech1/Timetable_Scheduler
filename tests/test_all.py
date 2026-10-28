"""
Automated Test Suite for AI Timetable Scheduler
"""
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_loader import DataLoader
from src.constraints import evaluate_timetable, get_session_conflicts
from src.csp_solver import solve_backtracking_baseline, solve_backtracking_heuristics
from src.min_conflicts import solve_min_conflicts
from src.simulated_annealing import solve_simulated_annealing
from src.hybrid_solver import solve_hybrid_csp_sa
from src.utils import export_to_csv_string, export_to_excel_bytes

def test_tiny_dataset():
    print("=== Testing Tiny Dataset ===")
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "tiny_dataset.json")
    subjects, teachers, rooms, classes, ts = DataLoader.load_json(data_path)
    sessions = DataLoader.generate_sessions(classes, subjects, teachers)
    domains = DataLoader.generate_domains(sessions, rooms, ts, teachers, classes)

    print(f"Tiny dataset: {len(sessions)} sessions to schedule.")
    res = solve_backtracking_heuristics(sessions, domains, timeout_seconds=10)
    assert res.success, "Heuristic backtracking should easily solve tiny dataset"
    rep = evaluate_timetable(res.assignment, rooms, teachers, classes, subjects, ts)
    assert rep.hard_count == 0, f"Tiny dataset should have 0 hard violations, got {rep.hard_count}"
    print(f"Tiny solved in {res.time_taken:.4f}s with {res.nodes_expanded} nodes. Violations: {rep.hard_count}")

def test_small_dataset():
    print("\n=== Testing Small Dataset ===")
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "small_dataset.json")
    subjects, teachers, rooms, classes, ts = DataLoader.load_json(data_path)
    sessions = DataLoader.generate_sessions(classes, subjects, teachers)
    domains = DataLoader.generate_domains(sessions, rooms, ts, teachers, classes)
    print(f"Small dataset: {len(sessions)} sessions to schedule.")

    # 1. Heuristic Backtracking
    res_heur = solve_backtracking_heuristics(sessions, domains, timeout_seconds=15)
    print(f"Heuristic Backtracking: Success={res_heur.success}, Time={res_heur.time_taken:.3f}s, Nodes={res_heur.nodes_expanded}")
    assert res_heur.success, "Heuristic backtracking must solve small dataset"
    rep_heur = evaluate_timetable(res_heur.assignment, rooms, teachers, classes, subjects, ts)
    print(f"Heuristic Backtracking Hard Violations: {rep_heur.hard_count}, Soft: {rep_heur.soft_penalty}")
    assert rep_heur.hard_count == 0, "Small dataset must be solved with 0 hard violations"

    # 2. Min-Conflicts
    res_mc = solve_min_conflicts(sessions, domains, rooms, teachers, classes, subjects, ts, max_steps=1500, timeout_seconds=15)
    print(f"Min-Conflicts: Success={res_mc.success}, Time={res_mc.time_taken:.3f}s, Steps={res_mc.iterations}, Hard={res_mc.hard_violations}, Soft={res_mc.soft_penalty}")
    assert res_mc.success, "Min-Conflicts must find a feasible solution"

    # 3. Hybrid CSP + SA
    res_hyb = solve_hybrid_csp_sa(sessions, domains, rooms, teachers, classes, subjects, ts, sa_iterations=500, timeout_seconds=15)
    print(f"Hybrid CSP+SA: Success={res_hyb.success}, Total Time={res_hyb.total_time:.3f}s, Initial Soft={res_hyb.initial_soft_penalty}, Final Soft={res_hyb.final_soft_penalty}, Hard={res_hyb.hard_violations}")
    assert res_hyb.hard_violations == 0, "Hybrid CSP+SA should maintain 0 hard violations"

    # Test export
    csv_str = export_to_csv_string(res_heur.assignment)
    assert len(csv_str) > 100, "CSV export should produce valid data"
    excel_bytes = export_to_excel_bytes(res_heur.assignment, classes, teachers, rooms, ts)
    assert len(excel_bytes) > 1000, "Excel export should produce valid workbook bytes"
    print("CSV and Excel exports verified!")

def test_large_dataset():
    print("\n=== Testing Large Dataset ===")
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "large_dataset.json")
    subjects, teachers, rooms, classes, ts = DataLoader.load_json(data_path)
    sessions = DataLoader.generate_sessions(classes, subjects, teachers)
    domains = DataLoader.generate_domains(sessions, rooms, ts, teachers, classes)
    print(f"Large dataset: {len(sessions)} sessions to schedule.")

    res_heur = solve_backtracking_heuristics(sessions, domains, timeout_seconds=20)
    print(f"Large Heuristics CSP: Success={res_heur.success}, Time={res_heur.time_taken:.3f}s, Nodes={res_heur.nodes_expanded}")
    assert res_heur.success, "Large dataset should be solved by heuristic CSP"
    rep_heur = evaluate_timetable(res_heur.assignment, rooms, teachers, classes, subjects, ts)
    assert rep_heur.hard_count == 0, f"Large dataset must have 0 hard violations, got {rep_heur.hard_count}"

if __name__ == "__main__":
    test_tiny_dataset()
    test_small_dataset()
    test_large_dataset()
    print("\nALL AUTOMATED UNIT TESTS PASSED SUCCESSFULLY! [OK]")
