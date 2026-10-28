"""
Constraint evaluation and violation counting module for AI Timetable Scheduler.
Implements:
- Hard Constraints H1-H9 + Hardened S3 (consecutive lab)
- Soft Constraints S1 (minimize gaps), S2 (spread lectures), S4 (teacher preferences), S5 (max consecutive teacher load)
- Cost function: Cost = 1000 * (hard violations) + (soft penalties)
- Live conflict pinpointing for Min-Conflicts local search and manual editing UI.
"""
from typing import Dict, List, Tuple, Any, Set, Optional
from collections import defaultdict
from .models import Session, SessionPlacement, Room, Teacher, ClassGroup, TimeStructure, Subject

class ConstraintWeights:
    HARD_VIOLATION = 1000
    S1_CLASS_GAP = 10
    S2_SAME_SUBJECT_SAME_DAY = 15
    S3_LAB_SPLIT = 1000  # Hard constraint per user confirmation
    S4_TEACHER_PREFERENCE = 10
    S5_TEACHER_CONSECUTIVE_OVER_2 = 15

class ViolationReport:
    def __init__(self):
        self.hard_violations: List[str] = []
        self.soft_violations: List[str] = []
        self.hard_count: int = 0
        self.soft_penalty: int = 0
        self.total_cost: int = 0

    def calculate_total(self):
        self.hard_count = len(self.hard_violations)
        self.total_cost = (self.hard_count * ConstraintWeights.HARD_VIOLATION) + self.soft_penalty
        return self.total_cost

    def to_dict(self):
        return {
            "hard_count": self.hard_count,
            "soft_penalty": self.soft_penalty,
            "total_cost": self.total_cost,
            "hard_violations": self.hard_violations,
            "soft_violations": self.soft_violations
        }

def evaluate_timetable(assignment: Dict[Session, SessionPlacement],
                       rooms: Dict[str, Room],
                       teachers: Dict[str, Teacher],
                       classes: Dict[str, ClassGroup],
                       subjects: Dict[str, Subject],
                       time_structure: TimeStructure) -> ViolationReport:
    """
    Evaluates a full or partial assignment against all H1-H9 hard constraints and S1-S5 soft constraints.
    Returns a comprehensive ViolationReport.
    """
    report = ViolationReport()

    # Track slot allocations
    # (day, period) -> list of (session, placement)
    teacher_slots = defaultdict(list)
    class_slots = defaultdict(list)
    room_slots = defaultdict(list)

    # Class daily periods: (class_name, day) -> list of periods
    class_daily_periods = defaultdict(list)
    # Teacher daily periods: (teacher_name, day) -> list of periods
    teacher_daily_periods = defaultdict(list)
    # Class-day subjects: (class_name, day, subject_code) -> count
    class_day_subjects = defaultdict(int)

    # 1. Evaluate individual placements & populate slot grids
    for session, placement in assignment.items():
        if placement is None:
            continue

        cg = classes[session.class_name]
        teacher = teachers.get(session.teacher_name)
        room = rooms.get(placement.room)
        sub = subjects.get(session.subject_code)

        # H4: Room capacity
        if room and room.capacity < cg.strength:
            report.hard_violations.append(
                f"H4 Capacity violation: Room '{room.name}' (cap {room.capacity}) < Class '{cg.name}' (strength {cg.strength}) for session {session.id}"
            )

        # H5: Room type
        if room:
            if session.session_type == 'lab' and room.type != 'lab':
                report.hard_violations.append(
                    f"H5 Room type violation: Lab session '{session.id}' placed in non-lab room '{room.name}'"
                )
            elif session.session_type == 'theory' and room.type != 'classroom':
                report.hard_violations.append(
                    f"H5 Room type violation: Theory session '{session.id}' placed in lab room '{room.name}'"
                )

        # H9: Lunch break overlap
        lunch_slot = cg.lunch_break_slot
        occupied_slots = placement.get_occupied_slots(session.duration)
        for day, period in occupied_slots:
            if period == lunch_slot:
                report.hard_violations.append(
                    f"H9 Lunch clash: Session '{session.id}' scheduled during Class '{cg.name}' lunch break (period {lunch_slot})"
                )

            # Check day bound overrun
            if period > time_structure.periods_per_day:
                report.hard_violations.append(
                    f"Out of bounds: Session '{session.id}' extends beyond max period {time_structure.periods_per_day}"
                )

            # H6: Teacher unavailable slot
            if teacher and (day, period) in teacher.unavailable_slots:
                report.hard_violations.append(
                    f"H6 Teacher unavailable: Prof. '{teacher.name}' scheduled at unavailable slot ({day}, period {period}) for {session.id}"
                )

            # Populate slots
            teacher_slots[(session.teacher_name, day, period)].append(session)
            class_slots[(session.class_name, day, period)].append(session)
            room_slots[(placement.room, day, period)].append(session)

            class_daily_periods[(session.class_name, day)].append(period)
            teacher_daily_periods[(session.teacher_name, day)].append(period)

        # Soft S4: Teacher preferences (e.g. avoid first period)
        if teacher and teacher.preferences.get("avoid_first_period", False):
            if any(period == 1 for _, period in occupied_slots):
                report.soft_penalty += ConstraintWeights.S4_TEACHER_PREFERENCE
                report.soft_violations.append(
                    f"S4 Preference: Prof. '{teacher.name}' prefers avoiding period 1, but session '{session.id}' scheduled there"
                )

        # Record subject occurrences per class per day
        class_day_subjects[(session.class_name, placement.day, session.subject_code)] += 1

    # 2. Check binary clashes: H1, H2, H3
    # H1: Teacher double booking
    for (tname, day, period), sess_list in teacher_slots.items():
        if len(sess_list) > 1:
            ids = [s.id for s in sess_list]
            report.hard_violations.append(
                f"H1 Teacher clash: Prof. '{tname}' double-booked at ({day}, period {period}) for sessions: {', '.join(ids)}"
            )

    # H2: Class double booking
    for (cname, day, period), sess_list in class_slots.items():
        if len(sess_list) > 1:
            ids = [s.id for s in sess_list]
            report.hard_violations.append(
                f"H2 Class clash: Class '{cname}' double-booked at ({day}, period {period}) for sessions: {', '.join(ids)}"
            )

    # H3: Room double booking
    for (rname, day, period), sess_list in room_slots.items():
        if len(sess_list) > 1:
            ids = [s.id for s in sess_list]
            report.hard_violations.append(
                f"H3 Room clash: Room '{rname}' double-booked at ({day}, period {period}) for sessions: {', '.join(ids)}"
            )

    # 3. Soft S1: Class gaps (idle periods between first and last class of the day, excluding lunch)
    for (cname, day), periods in class_daily_periods.items():
        if len(periods) > 1:
            cg = classes[cname]
            min_p = min(periods)
            max_p = max(periods)
            assigned_set = set(periods)
            gaps = 0
            for p in range(min_p, max_p + 1):
                if p not in assigned_set and p != cg.lunch_break_slot and p not in time_structure.break_periods:
                    gaps += 1
            if gaps > 0:
                report.soft_penalty += gaps * ConstraintWeights.S1_CLASS_GAP
                report.soft_violations.append(
                    f"S1 Class gap: Class '{cname}' has {gaps} free period gap(s) on {day}"
                )

    # 4. Soft S2: Spread subject lectures across different days
    for (cname, day, sc), count in class_day_subjects.items():
        sub = subjects.get(sc)
        if sub and sub.type == 'theory' and count > 1:
            excess = count - 1
            report.soft_penalty += excess * ConstraintWeights.S2_SAME_SUBJECT_SAME_DAY
            report.soft_violations.append(
                f"S2 Subject clustering: Class '{cname}' has {count} lectures of {sc} on {day} (should be spread)"
            )

    # 5. Soft S5: Avoid > 2 consecutive lectures for a teacher
    for (tname, day), periods in teacher_daily_periods.items():
        sorted_p = sorted(set(periods))
        consecutive = 1
        for i in range(1, len(sorted_p)):
            if sorted_p[i] == sorted_p[i-1] + 1:
                consecutive += 1
                if consecutive > 2:
                    report.soft_penalty += ConstraintWeights.S5_TEACHER_CONSECUTIVE_OVER_2
                    report.soft_violations.append(
                        f"S5 Teacher fatigue: Prof. '{tname}' has >2 consecutive lectures on {day} (at period {sorted_p[i]})"
                    )
            else:
                consecutive = 1

    report.calculate_total()
    return report

def get_session_conflicts(session: Session,
                          placement: SessionPlacement,
                          current_assignment: Dict[Session, SessionPlacement],
                          rooms: Dict[str, Room],
                          teachers: Dict[str, Teacher],
                          classes: Dict[str, ClassGroup],
                          subjects: Dict[str, Subject],
                          time_structure: TimeStructure) -> List[str]:
    """
    Returns specific hard conflict descriptions for placing `session` at `placement`,
    assuming other sessions are placed as in `current_assignment`.
    Used by Min-Conflicts and the UI manual editor.
    """
    conflicts = []
    cg = classes[session.class_name]
    teacher = teachers.get(session.teacher_name)
    room = rooms.get(placement.room)
    occupied_slots = placement.get_occupied_slots(session.duration)

    # Unary checks
    if room and room.capacity < cg.strength:
        conflicts.append(f"Room capacity ({room.capacity}) is less than class strength ({cg.strength})")

    if room:
        if session.session_type == 'lab' and room.type != 'lab':
            conflicts.append(f"Lab session placed in non-lab room '{room.name}'")
        elif session.session_type == 'theory' and room.type != 'classroom':
            conflicts.append(f"Theory session placed in lab room '{room.name}'")

    for day, period in occupied_slots:
        if period == cg.lunch_break_slot:
            conflicts.append(f"Overlaps with Class {cg.name} lunch break at period {period}")
        if period > time_structure.periods_per_day:
            conflicts.append(f"Exceeds daily period limit ({time_structure.periods_per_day})")
        if teacher and (day, period) in teacher.unavailable_slots:
            conflicts.append(f"Teacher {teacher.name} is unavailable at ({day}, period {period})")

    # Binary clash checks against existing assignments
    for other_session, other_placement in current_assignment.items():
        if other_session == session or other_placement is None:
            continue

        other_slots = other_placement.get_occupied_slots(other_session.duration)
        # Check slot intersection
        common_slots = set(occupied_slots).intersection(set(other_slots))
        if not common_slots:
            continue

        for day, period in common_slots:
            # H1: Teacher clash
            if session.teacher_name == other_session.teacher_name:
                conflicts.append(
                    f"Teacher {session.teacher_name} already teaching '{other_session.id}' at ({day}, period {period})"
                )
            # H2: Class clash
            if session.class_name == other_session.class_name:
                conflicts.append(
                    f"Class {session.class_name} already has session '{other_session.id}' at ({day}, period {period})"
                )
            # H3: Room clash
            if placement.room == other_placement.room:
                conflicts.append(
                    f"Room {placement.room} already booked for '{other_session.id}' at ({day}, period {period})"
                )

    return conflicts
