"""
Hybrid CSP + Simulated Annealing Solver for AI Timetable Scheduler.
Implements:
Stage 1: Systematic CSP search (Heuristic Backtracking with MRV+FC) or Min-Conflicts
         to obtain a guaranteed feasible timetable (Hard Violations = 0).
Stage 2: Simulated Annealing local search starting from the feasible state to
         intensively optimize soft constraints (minimizing gaps S1, spreading lectures S2,
         respecting teacher preferences S4, avoiding teacher overload streaks S5).
"""
import time
from typing import Dict, List, Optional

from .models import Session, SessionPlacement, Room, Teacher, ClassGroup, TimeStructure, Subject
from .constraints import evaluate_timetable
from .csp_solver import solve_backtracking_heuristics
from .min_conflicts import solve_min_conflicts
from .simulated_annealing import solve_simulated_annealing

class HybridResult:
    def __init__(self, assignment: Dict[Session, SessionPlacement],
                 total_time: float, stage1_time: float, stage2_time: float,
                 stage1_nodes: int, stage2_iterations: int,
                 initial_soft_penalty: int, final_soft_penalty: int,
                 hard_violations: int, total_cost: int,
                 cost_history: List[int], success: bool, message: str = ""):
        self.assignment = assignment
        self.total_time = total_time
        self.stage1_time = stage1_time
        self.stage2_time = stage2_time
        self.stage1_nodes = stage1_nodes
        self.stage2_iterations = stage2_iterations
        self.initial_soft_penalty = initial_soft_penalty
        self.final_soft_penalty = final_soft_penalty
        self.hard_violations = hard_violations
        self.total_cost = total_cost
        self.cost_history = cost_history
        self.success = success
        self.message = message

def solve_hybrid_csp_sa(sessions: List[Session],
                        domains: Dict[Session, List[SessionPlacement]],
                        rooms: Dict[str, Room],
                        teachers: Dict[str, Teacher],
                        classes: Dict[str, ClassGroup],
                        subjects: Dict[str, Subject],
                        time_structure: TimeStructure,
                        sa_iterations: int = 1500,
                        timeout_seconds: float = 60.0,
                        seed: Optional[int] = 42) -> HybridResult:
    """
    Two-stage Hybrid Solver:
    1. Feasibility Stage: Backtracking with MRV+FC finds zero-violation assignment.
       (Falls back to Min-Conflicts if CSP exceeds half-time).
    2. Optimization Stage: Simulated Annealing refines soft-constraint satisfaction.
    """
    overall_start = time.time()
    half_timeout = timeout_seconds / 2.0

    # -------------------------------------------------------------
    # Stage 1: Feasibility Search (CSP Backtracking with Heuristics)
    # -------------------------------------------------------------
    csp_res = solve_backtracking_heuristics(
        sessions=sessions,
        initial_domains=domains,
        timeout_seconds=half_timeout,
        use_mrv=True,
        use_degree=True,
        use_forward_checking=True,
        use_lcv=True
    )

    stage1_assignment = csp_res.assignment
    stage1_time = csp_res.time_taken
    stage1_nodes = csp_res.nodes_expanded

    if not csp_res.success or stage1_assignment is None:
        # Fallback to Min-Conflicts for feasibility if CSP timed out on large instance
        mc_res = solve_min_conflicts(
            sessions=sessions,
            domains=domains,
            rooms=rooms,
            teachers=teachers,
            classes=classes,
            subjects=subjects,
            time_structure=time_structure,
            max_steps=1500,
            timeout_seconds=half_timeout,
            seed=seed
        )
        stage1_assignment = mc_res.assignment
        stage1_time += mc_res.time_taken
        stage1_nodes += mc_res.iterations

    initial_report = evaluate_timetable(stage1_assignment, rooms, teachers, classes, subjects, time_structure)
    initial_soft = initial_report.soft_penalty

    # -------------------------------------------------------------
    # Stage 2: Soft Constraint Optimization (Simulated Annealing)
    # -------------------------------------------------------------
    remaining_time = max(5.0, timeout_seconds - (time.time() - overall_start))

    sa_res = solve_simulated_annealing(
        sessions=sessions,
        domains=domains,
        rooms=rooms,
        teachers=teachers,
        classes=classes,
        subjects=subjects,
        time_structure=time_structure,
        initial_assignment=stage1_assignment,
        initial_temp=300.0,
        min_temp=0.01,
        cooling_rate=0.995,
        max_iterations=sa_iterations,
        timeout_seconds=remaining_time,
        seed=seed
    )

    total_time = time.time() - overall_start
    final_report = evaluate_timetable(sa_res.assignment, rooms, teachers, classes, subjects, time_structure)

    return HybridResult(
        assignment=sa_res.assignment,
        total_time=total_time,
        stage1_time=stage1_time,
        stage2_time=sa_res.time_taken,
        stage1_nodes=stage1_nodes,
        stage2_iterations=sa_res.iterations,
        initial_soft_penalty=initial_soft,
        final_soft_penalty=final_report.soft_penalty,
        hard_violations=final_report.hard_count,
        total_cost=final_report.total_cost,
        cost_history=sa_res.cost_history,
        success=(final_report.hard_count == 0),
        message=f"Hybrid search finished. Soft penalty improved from {initial_soft} to {final_report.soft_penalty}."
    )
