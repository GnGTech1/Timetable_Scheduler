"""
High-Performance CSP Solvers for AI Timetable Scheduler:
1. Baseline Backtracking (chronological DFS).
2. Heuristic Backtracking (MRV + Degree Heuristic + Forward Checking).
Uses O(1) slot occupancy hash tables and clean Timeout unwinding.
"""
import time
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

from .models import Session, SessionPlacement, Room, Teacher, ClassGroup, TimeStructure, Subject
from .constraints import evaluate_timetable

class CSPSolverResult:
    def __init__(self, assignment: Optional[Dict[Session, SessionPlacement]],
                 time_taken: float, nodes_expanded: int, success: bool,
                 algorithm_name: str, message: str = ""):
        self.assignment = assignment
        self.time_taken = time_taken
        self.nodes_expanded = nodes_expanded
        self.success = success
        self.algorithm_name = algorithm_name
        self.message = message

# -------------------------------------------------------------
# 1. Baseline Plain Backtracking
# -------------------------------------------------------------
def solve_backtracking_baseline(sessions: List[Session],
                                initial_domains: Dict[Session, List[SessionPlacement]],
                                timeout_seconds: float = 30.0) -> CSPSolverResult:
    """
    Plain DFS Backtracking:
    - Fixed chronological variable ordering.
    - Fixed domain order.
    - No forward checking / inference.
    - Clean timeout exception handling.
    """
    start_time = time.time()
    nodes_expanded = 0
    assignment: Dict[Session, SessionPlacement] = {}

    # Fast O(1) occupancy sets
    teacher_occ = set()  # (teacher_name, day, period)
    class_occ = set()    # (class_name, day, period)
    room_occ = set()     # (room_name, day, period)

    def is_valid(var: Session, val: SessionPlacement) -> bool:
        for i in range(var.duration):
            p = val.period + i
            if (var.teacher_name, val.day, p) in teacher_occ:
                return False
            if (var.class_name, val.day, p) in class_occ:
                return False
            if (val.room, val.day, p) in room_occ:
                return False
        return True

    def place(var: Session, val: SessionPlacement):
        assignment[var] = val
        for i in range(var.duration):
            p = val.period + i
            teacher_occ.add((var.teacher_name, val.day, p))
            class_occ.add((var.class_name, val.day, p))
            room_occ.add((val.room, val.day, p))

    def unplace(var: Session, val: SessionPlacement):
        del assignment[var]
        for i in range(var.duration):
            p = val.period + i
            teacher_occ.remove((var.teacher_name, val.day, p))
            class_occ.remove((var.class_name, val.day, p))
            room_occ.remove((val.room, val.day, p))

    def backtrack(idx: int) -> bool:
        nonlocal nodes_expanded
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("Baseline timeout reached")

        if idx == len(sessions):
            return True

        var = sessions[idx]
        for val in initial_domains.get(var, []):
            nodes_expanded += 1
            if is_valid(var, val):
                place(var, val)
                if backtrack(idx + 1):
                    return True
                unplace(var, val)

        return False

    try:
        success = backtrack(0)
    except TimeoutError:
        success = False

    elapsed = time.time() - start_time
    msg = "Solved successfully." if success else ("Timed out (Exponential search space for un-pruned DFS)" if elapsed >= timeout_seconds else "No solution found")

    return CSPSolverResult(
        assignment=assignment if success else None,
        time_taken=elapsed,
        nodes_expanded=nodes_expanded,
        success=success,
        algorithm_name="Backtracking (Baseline)",
        message=msg
    )

# -------------------------------------------------------------
# 2. Heuristic Backtracking (MRV + Degree + Forward Checking)
# -------------------------------------------------------------
def solve_backtracking_heuristics(sessions: List[Session],
                                  initial_domains: Dict[Session, List[SessionPlacement]],
                                  timeout_seconds: float = 60.0,
                                  use_mrv: bool = True,
                                  use_degree: bool = True,
                                  use_forward_checking: bool = True,
                                  use_lcv: bool = False) -> CSPSolverResult:
    """
    Optimized Backtracking with:
    - Minimum Remaining Values (MRV): pick variable with fewest legal values in active domain.
    - Degree Heuristic: tie-breaker for MRV.
    - Forward Checking: validates against future variables sharing teacher, class, or room.
    - O(1) slot occupancy lookup tables.
    """
    start_time = time.time()
    nodes_expanded = 0
    assignment: Dict[Session, SessionPlacement] = {}

    # Fast O(1) occupancy sets
    teacher_occ = set()  # (teacher_name, day, period)
    class_occ = set()    # (class_name, day, period)
    room_occ = set()     # (room_name, day, period)

    # Active domains
    curr_domains: Dict[Session, List[SessionPlacement]] = {
        s: list(initial_domains.get(s, [])) for s in sessions
    }

    # Precompute constraint graph neighbors (sessions sharing teacher or class)
    neighbors: Dict[Session, List[Session]] = defaultdict(list)
    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):
            s1 = sessions[i]
            s2 = sessions[j]
            if s1.class_name == s2.class_name or s1.teacher_name == s2.teacher_name:
                neighbors[s1].append(s2)
                neighbors[s2].append(s1)

    def is_consistent(var: Session, val: SessionPlacement) -> bool:
        for i in range(var.duration):
            p = val.period + i
            if (var.teacher_name, val.day, p) in teacher_occ:
                return False
            if (var.class_name, val.day, p) in class_occ:
                return False
            if (val.room, val.day, p) in room_occ:
                return False
        return True

    def place(var: Session, val: SessionPlacement):
        assignment[var] = val
        for i in range(var.duration):
            p = val.period + i
            teacher_occ.add((var.teacher_name, val.day, p))
            class_occ.add((var.class_name, val.day, p))
            room_occ.add((val.room, val.day, p))

    def unplace(var: Session, val: SessionPlacement):
        del assignment[var]
        for i in range(var.duration):
            p = val.period + i
            teacher_occ.remove((var.teacher_name, val.day, p))
            class_occ.remove((var.class_name, val.day, p))
            room_occ.remove((val.room, val.day, p))

    def select_variable() -> Optional[Session]:
        unassigned = [s for s in sessions if s not in assignment]
        if not unassigned:
            return None

        if not use_mrv:
            return unassigned[0]

        # Prioritize labs (duration=2) and smallest active domain
        def mrv_key(s: Session):
            # Labs first, then smallest domain size, then negative degree for tie-break
            dom_len = len(curr_domains[s])
            deg = len([n for n in neighbors[s] if n not in assignment]) if use_degree else 0
            # Higher priority for longer duration (labs are harder to fit)
            return (-s.duration, dom_len, -deg)

        return min(unassigned, key=mrv_key)

    def forward_check(var: Session, val: SessionPlacement) -> Tuple[bool, Dict[Session, List[SessionPlacement]]]:
        """Prunes inconsistent values from unassigned neighbors."""
        val_slots = [(val.day, val.period + i) for i in range(var.duration)]
        val_slots_set = set(val_slots)
        pruned = defaultdict(list)

        # Check neighbors sharing teacher or class
        for n in neighbors[var]:
            if n in assignment:
                continue

            shares_teacher = (var.teacher_name == n.teacher_name)
            shares_class = (var.class_name == n.class_name)

            new_dom = []
            for n_val in curr_domains[n]:
                clash = False
                if shares_teacher or shares_class:
                    for i in range(n.duration):
                        if (n_val.day, n_val.period + i) in val_slots_set:
                            clash = True
                            break
                elif n_val.room == val.room:
                    for i in range(n.duration):
                        if (n_val.day, n_val.period + i) in val_slots_set:
                            clash = True
                            break

                if clash:
                    pruned[n].append(n_val)
                else:
                    new_dom.append(n_val)

            if not new_dom:
                # Wipeout! Restore
                for r_sess, rem_list in pruned.items():
                    curr_domains[r_sess].extend(rem_list)
                return False, {}

            curr_domains[n] = new_dom

        return True, pruned

    def backtrack() -> bool:
        nonlocal nodes_expanded
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError("Heuristics timeout reached")

        if len(assignment) == len(sessions):
            return True

        var = select_variable()
        if var is None:
            return True

        domain_vals = list(curr_domains[var])

        for val in domain_vals:
            nodes_expanded += 1
            if not is_consistent(var, val):
                continue

            # Forward check
            if use_forward_checking:
                fc_ok, pruned = forward_check(var, val)
                if not fc_ok:
                    continue
            else:
                pruned = {}

            place(var, val)

            if backtrack():
                return True

            unplace(var, val)
            if use_forward_checking:
                for n, rem_list in pruned.items():
                    curr_domains[n].extend(rem_list)

        return False

    try:
        success = backtrack()
    except TimeoutError:
        success = False

    elapsed = time.time() - start_time
    msg = "Solved successfully." if success else ("Timed out" if elapsed >= timeout_seconds else "No solution found")

    return CSPSolverResult(
        assignment=assignment if success else None,
        time_taken=elapsed,
        nodes_expanded=nodes_expanded,
        success=success,
        algorithm_name="Backtracking (MRV + Degree + FC)",
        message=msg
    )
