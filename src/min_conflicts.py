"""
Min-Conflicts Local Search Algorithm for AI Timetable Scheduler.
Implements:
- Initial complete assignment (greedy or random from unary-valid domains)
- Conflicted variable selection
- Value selection minimizing conflict score with random tie-breaking
- Plateau escape via Random Walk (probability p) and Random Restart
- Cost history tracking for cost vs iterations convergence graph.
"""
import time
import random
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

from .models import Session, SessionPlacement, Room, Teacher, ClassGroup, TimeStructure, Subject
from .constraints import evaluate_timetable, get_session_conflicts, ConstraintWeights

class MinConflictsResult:
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

def count_conflicts_for_variable(var: Session,
                                 placement: SessionPlacement,
                                 current_assignment: Dict[Session, SessionPlacement]) -> int:
    """
    Fast binary clash count for (var, placement) against current assignment.
    """
    placed_slots = set(placement.get_occupied_slots(var.duration))
    conflicts = 0

    for other_var, other_plc in current_assignment.items():
        if other_var == var or other_plc is None:
            continue

        same_teacher = (var.teacher_name == other_var.teacher_name)
        same_class = (var.class_name == other_var.class_name)
        same_room = (placement.room == other_plc.room)

        if not (same_teacher or same_class or same_room):
            continue

        other_slots = other_plc.get_occupied_slots(other_var.duration)
        if placed_slots.intersection(other_slots):
            conflicts += 1

    return conflicts

def get_all_conflicted_variables(sessions: List[Session],
                                 assignment: Dict[Session, SessionPlacement]) -> List[Session]:
    """
    Identifies all variables currently involved in at least one conflict.
    """
    conflicted = []
    # Build slot occupancy maps: slot -> list of sessions
    teacher_occ = defaultdict(list)
    class_occ = defaultdict(list)
    room_occ = defaultdict(list)

    for s, plc in assignment.items():
        for slot in plc.get_occupied_slots(s.duration):
            teacher_occ[(s.teacher_name, slot)].append(s)
            class_occ[(s.class_name, slot)].append(s)
            room_occ[(plc.room, slot)].append(s)

    conflicted_set = set()
    for s_list in teacher_occ.values():
        if len(s_list) > 1:
            conflicted_set.update(s_list)
    for s_list in class_occ.values():
        if len(s_list) > 1:
            conflicted_set.update(s_list)
    for s_list in room_occ.values():
        if len(s_list) > 1:
            conflicted_set.update(s_list)

    return list(conflicted_set)

def solve_min_conflicts(sessions: List[Session],
                        domains: Dict[Session, List[SessionPlacement]],
                        rooms: Dict[str, Room],
                        teachers: Dict[str, Teacher],
                        classes: Dict[str, ClassGroup],
                        subjects: Dict[str, Subject],
                        time_structure: TimeStructure,
                        max_steps: int = 2000,
                        random_walk_prob: float = 0.08,
                        max_restarts: int = 2,
                        timeout_seconds: float = 60.0,
                        seed: Optional[int] = 42) -> MinConflictsResult:
    """
    Solves timetable using Min-Conflicts heuristic with plateau escape:
    - Initial complete assignment generated greedily or randomly from legal domains.
    - At each iteration, pick a random conflicted variable.
    - Evaluate candidate values in domain; pick value minimizing conflicts (tie-break randomly).
    - With probability `random_walk_prob`, pick a random domain value to escape local minima.
    - If stuck in a plateau for too many iterations, trigger a random restart.
    """
    if seed is not None:
        random.seed(seed)

    start_time = time.time()
    best_assignment = None
    best_cost = float('inf')
    best_hard_violations = float('inf')
    cost_history = []
    total_iterations = 0

    for restart_idx in range(max_restarts + 1):
        if time.time() - start_time > timeout_seconds:
            break

        # 1. Initial complete assignment: Greedy initialization
        current_assignment: Dict[Session, SessionPlacement] = {}
        for session in sessions:
            cand_vals = domains.get(session, [])
            if not cand_vals:
                continue
            # Pick value with minimum conflicts so far
            if random.random() < 0.3:
                chosen_val = random.choice(cand_vals)
            else:
                min_c = float('inf')
                best_cand = []
                for val in cand_vals:
                    c = count_conflicts_for_variable(session, val, current_assignment)
                    if c < min_c:
                        min_c = c
                        best_cand = [val]
                    elif c == min_c:
                        best_cand.append(val)
                chosen_val = random.choice(best_cand)
            current_assignment[session] = chosen_val

        # 2. Iterative repair loop
        for step in range(max_steps):
            total_iterations += 1
            if time.time() - start_time > timeout_seconds:
                break

            # Find conflicted variables
            conflicted_vars = get_all_conflicted_variables(sessions, current_assignment)

            # Record cost periodically or every step for first 300 steps
            if step < 300 or step % 5 == 0 or len(conflicted_vars) == 0:
                report = evaluate_timetable(current_assignment, rooms, teachers, classes, subjects, time_structure)
                cost_history.append(report.total_cost)
                if report.total_cost < best_cost:
                    best_cost = report.total_cost
                    best_hard_violations = report.hard_count
                    best_assignment = dict(current_assignment)

            if not conflicted_vars:
                # 0 hard conflicts! Feasible timetable reached!
                elapsed = time.time() - start_time
                final_rep = evaluate_timetable(current_assignment, rooms, teachers, classes, subjects, time_structure)
                return MinConflictsResult(
                    assignment=current_assignment,
                    time_taken=elapsed,
                    iterations=total_iterations,
                    success=True,
                    cost_history=cost_history,
                    hard_violations=final_rep.hard_count,
                    soft_penalty=final_rep.soft_penalty,
                    total_cost=final_rep.total_cost,
                    message=f"Feasible solution found in {total_iterations} iterations."
                )

            # Pick a conflicted variable at random
            var = random.choice(conflicted_vars)
            var_domain = domains.get(var, [])
            if not var_domain:
                continue

            # Plateau escape: random walk
            if random.random() < random_walk_prob:
                current_assignment[var] = random.choice(var_domain)
            else:
                # Find values that minimize conflicts
                min_conflicts = float('inf')
                best_values = []
                for val in var_domain:
                    conf = count_conflicts_for_variable(var, val, current_assignment)
                    if conf < min_conflicts:
                        min_conflicts = conf
                        best_values = [val]
                    elif conf == min_conflicts:
                        best_values.append(val)

                # Random tie-breaking among best values
                current_assignment[var] = random.choice(best_values)

    elapsed = time.time() - start_time
    final_rep = evaluate_timetable(best_assignment if best_assignment else current_assignment,
                                   rooms, teachers, classes, subjects, time_structure)

    return MinConflictsResult(
        assignment=best_assignment if best_assignment else current_assignment,
        time_taken=elapsed,
        iterations=total_iterations,
        success=(final_rep.hard_count == 0),
        cost_history=cost_history,
        hard_violations=final_rep.hard_count,
        soft_penalty=final_rep.soft_penalty,
        total_cost=final_rep.total_cost,
        message="Feasible solution found." if final_rep.hard_count == 0 else f"Stopped with {final_rep.hard_count} hard violations remaining."
    )
