"""
Simulated Annealing Local Search Algorithm for AI Timetable Scheduler.
Implements:
- Initial state generation
- Neighborhood moves:
  1. Relocate: Move a session to a new valid placement from its domain.
  2. Swap: Swap placements of two sessions (matching session types & room compatibilities).
- Exponential cooling schedule: T_{k+1} = alpha * T_k
- Metropolis acceptance criterion: P = exp(-delta_E / T)
- Cost trajectory recording for convergence visualization.
"""
import time
import math
import random
from typing import Dict, List, Tuple, Optional, Any

from .models import Session, SessionPlacement, Room, Teacher, ClassGroup, TimeStructure, Subject
from .constraints import evaluate_timetable

class SAResult:
    def __init__(self, assignment: Dict[Session, SessionPlacement],
                 time_taken: float, iterations: int, success: bool,
                 cost_history: List[int], hard_violations: int,
                 soft_penalty: int, total_cost: int, message: str = ""):
        self.assignment = assignment
        self.time_taken = time_taken
        self.iterations = iterations
        self.success = success
        self.cost_history = cost_history
        self.hard_violations = hard_violations
        self.soft_penalty = soft_penalty
        self.total_cost = total_cost
        self.message = message

def solve_simulated_annealing(sessions: List[Session],
                              domains: Dict[Session, List[SessionPlacement]],
                              rooms: Dict[str, Room],
                              teachers: Dict[str, Teacher],
                              classes: Dict[str, ClassGroup],
                              subjects: Dict[str, Subject],
                              time_structure: TimeStructure,
                              initial_assignment: Optional[Dict[Session, SessionPlacement]] = None,
                              initial_temp: float = 1000.0,
                              min_temp: float = 0.05,
                              cooling_rate: float = 0.995,
                              max_iterations: int = 3000,
                              timeout_seconds: float = 60.0,
                              seed: Optional[int] = 42) -> SAResult:
    """
    Simulated Annealing solver.
    If `initial_assignment` is provided, starts from it (used by Hybrid CSP + SA).
    Otherwise, generates an initial assignment from unary-valid domains.
    """
    if seed is not None:
        random.seed(seed)

    start_time = time.time()

    # 1. Initialize assignment
    if initial_assignment:
        current_assignment = dict(initial_assignment)
    else:
        current_assignment = {}
        for s in sessions:
            cand = domains.get(s, [])
            current_assignment[s] = random.choice(cand) if cand else None

    # Calculate initial cost
    current_report = evaluate_timetable(current_assignment, rooms, teachers, classes, subjects, time_structure)
    current_cost = current_report.total_cost

    best_assignment = dict(current_assignment)
    best_cost = current_cost
    best_hard = current_report.hard_count
    best_soft = current_report.soft_penalty

    cost_history = [current_cost]
    T = initial_temp
    iteration = 0

    while T > min_temp and iteration < max_iterations:
        if time.time() - start_time > timeout_seconds:
            break

        iteration += 1

        # 2. Neighborhood move
        move_type = random.random()
        s1 = random.choice(sessions)
        old_plc1 = current_assignment[s1]

        if move_type < 0.65 or len(sessions) < 2:
            # Move 1: Relocate session s1 to a new placement
            cand_vals = domains.get(s1, [])
            if not cand_vals:
                continue
            new_plc1 = random.choice(cand_vals)
            current_assignment[s1] = new_plc1

            new_report = evaluate_timetable(current_assignment, rooms, teachers, classes, subjects, time_structure)
            delta_E = new_report.total_cost - current_cost

            # Acceptance decision
            if delta_E < 0 or (T > 0 and random.random() < math.exp(-delta_E / T)):
                current_cost = new_report.total_cost
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_hard = new_report.hard_count
                    best_soft = new_report.soft_penalty
                    best_assignment = dict(current_assignment)
            else:
                # Reject move
                current_assignment[s1] = old_plc1
        else:
            # Move 2: Swap placements of two compatible sessions
            s2 = random.choice(sessions)
            if s1 == s2:
                continue

            old_plc2 = current_assignment[s2]
            # Check compatibility: duration and session type must match
            if s1.duration == s2.duration and s1.session_type == s2.session_type:
                # Perform swap
                current_assignment[s1] = old_plc2
                current_assignment[s2] = old_plc1

                new_report = evaluate_timetable(current_assignment, rooms, teachers, classes, subjects, time_structure)
                delta_E = new_report.total_cost - current_cost

                if delta_E < 0 or (T > 0 and random.random() < math.exp(-delta_E / T)):
                    current_cost = new_report.total_cost
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_hard = new_report.hard_count
                        best_soft = new_report.soft_penalty
                        best_assignment = dict(current_assignment)
                else:
                    # Reject swap
                    current_assignment[s1] = old_plc1
                    current_assignment[s2] = old_plc2

        # Record cost history periodically
        if iteration < 300 or iteration % 10 == 0:
            cost_history.append(current_cost)

        # Cool down
        T *= cooling_rate

        # Early exit if perfect cost 0 reached
        if best_cost == 0:
            break

    elapsed = time.time() - start_time
    final_rep = evaluate_timetable(best_assignment, rooms, teachers, classes, subjects, time_structure)

    return SAResult(
        assignment=best_assignment,
        time_taken=elapsed,
        iterations=iteration,
        success=(final_rep.hard_count == 0),
        cost_history=cost_history,
        hard_violations=final_rep.hard_count,
        soft_penalty=final_rep.soft_penalty,
        total_cost=final_rep.total_cost,
        message=f"Simulated Annealing completed {iteration} iterations."
    )
