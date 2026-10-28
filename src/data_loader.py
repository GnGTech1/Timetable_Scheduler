"""
Data loader and validation module for AI Timetable Scheduler.
Supports JSON, CSV, automated teacher load-balancing (Option B),
solvability validation, and CSP variable/domain generation.
"""
import os
import json
import csv
from typing import Dict, List, Tuple, Any, Optional

from .models import (
    Subject, Teacher, Room, ClassGroup, TimeStructure,
    Session, SessionPlacement
)

class DataValidationError(Exception):
    pass

class DataLoader:
    @staticmethod
    def load_json(filepath_or_data) -> Tuple[Dict[str, Subject], Dict[str, Teacher], Dict[str, Room], Dict[str, ClassGroup], TimeStructure]:
        if isinstance(filepath_or_data, str):
            with open(filepath_or_data, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = filepath_or_data

        # Time structure
        ts_data = data.get("time_structure", {})
        time_structure = TimeStructure(
            working_days=ts_data.get("working_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]),
            periods_per_day=ts_data.get("periods_per_day", 6),
            break_periods=ts_data.get("break_periods", [4])
        )

        # Subjects
        subjects = {}
        for s in data.get("subjects", []):
            subjects[s["code"]] = Subject(
                code=s["code"],
                name=s["name"],
                weekly_hours=int(s["weekly_hours"]),
                type=s.get("type", "theory").lower()
            )

        # Teachers
        teachers = {}
        for t in data.get("teachers", []):
            unavail = [(slot[0], int(slot[1])) for slot in t.get("unavailable_slots", [])]
            teachers[t["name"]] = Teacher(
                name=t["name"],
                subjects=t.get("subjects", []),
                unavailable_slots=unavail,
                max_weekly_load=int(t.get("max_weekly_load", 20)),
                preferences=t.get("preferences", {})
            )

        # Rooms
        rooms = {}
        for r in data.get("rooms", []):
            rooms[r["name"]] = Room(
                name=r["name"],
                capacity=int(r["capacity"]),
                type=r.get("type", "classroom").lower()
            )

        # Classes
        classes = {}
        for c in data.get("classes", []):
            classes[c["name"]] = ClassGroup(
                name=c["name"],
                strength=int(c["strength"]),
                subjects=c.get("subjects", []),
                lunch_break_slot=int(c.get("lunch_break_slot", time_structure.break_periods[0] if time_structure.break_periods else 4)),
                subject_teacher_map=c.get("subject_teacher_map", {})
            )

        return subjects, teachers, rooms, classes, time_structure

    @staticmethod
    def load_csv(directory_path: str) -> Tuple[Dict[str, Subject], Dict[str, Teacher], Dict[str, Room], Dict[str, ClassGroup], TimeStructure]:
        # Load time structure
        ts_file = os.path.join(directory_path, "time_structure.csv")
        working_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        periods_per_day = 6
        break_periods = [4]
        if os.path.exists(ts_file):
            with open(ts_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    working_days = [d.strip() for d in row["working_days"].split(",")]
                    periods_per_day = int(row["periods_per_day"])
                    break_periods = [int(p.strip()) for p in row["break_periods"].split(",")]
        time_structure = TimeStructure(working_days, periods_per_day, break_periods)

        # Load subjects
        subjects = {}
        sub_file = os.path.join(directory_path, "subjects.csv")
        if os.path.exists(sub_file):
            with open(sub_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row["code"].strip()
                    subjects[code] = Subject(
                        code=code,
                        name=row["name"].strip(),
                        weekly_hours=int(row["weekly_hours"]),
                        type=row.get("type", "theory").strip().lower()
                    )

        # Load teachers
        teachers = {}
        tea_file = os.path.join(directory_path, "teachers.csv")
        if os.path.exists(tea_file):
            with open(tea_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row["name"].strip()
                    sub_list = [s.strip() for s in row["subjects"].split(",") if s.strip()]
                    unavail_raw = row.get("unavailable_slots", "").strip()
                    unavail = []
                    if unavail_raw:
                        for entry in unavail_raw.split(";"):
                            if ":" in entry:
                                d, p = entry.split(":")
                                unavail.append((d.strip(), int(p.strip())))
                    pref = {"avoid_first_period": row.get("avoid_first_period", "false").lower() == "true"}
                    teachers[name] = Teacher(
                        name=name,
                        subjects=sub_list,
                        unavailable_slots=unavail,
                        max_weekly_load=int(row.get("max_weekly_load", 20)),
                        preferences=pref
                    )

        # Load rooms
        rooms = {}
        room_file = os.path.join(directory_path, "rooms.csv")
        if os.path.exists(room_file):
            with open(room_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rname = row["name"].strip()
                    rooms[rname] = Room(
                        name=rname,
                        capacity=int(row["capacity"]),
                        type=row.get("type", "classroom").strip().lower()
                    )

        # Load classes
        classes = {}
        class_file = os.path.join(directory_path, "classes.csv")
        if os.path.exists(class_file):
            with open(class_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cname = row["name"].strip()
                    sub_list = [s.strip() for s in row["subjects"].split(",") if s.strip()]
                    teacher_map = {}
                    tmap_raw = row.get("teacher_mapping", "").strip()
                    if tmap_raw:
                        for item in tmap_raw.split(";"):
                            if ":" in item:
                                sc, tn = item.split(":")
                                teacher_map[sc.strip()] = tn.strip()
                    classes[cname] = ClassGroup(
                        name=cname,
                        strength=int(row["strength"]),
                        subjects=sub_list,
                        lunch_break_slot=int(row.get("lunch_break_slot", break_periods[0] if break_periods else 4)),
                        subject_teacher_map=teacher_map
                    )

        return subjects, teachers, rooms, classes, time_structure

    @staticmethod
    def auto_assign_teachers_if_needed(classes: Dict[str, ClassGroup], teachers: Dict[str, Teacher], subjects: Dict[str, Subject]):
        """
        Implements Option B: Smart teacher load balancing.
        If a class subject does not have a designated teacher, assign the qualified
        teacher with the lowest current load without exceeding max_weekly_load.
        """
        # Calculate current load
        teacher_loads = {tname: 0 for tname in teachers}
        for cg in classes.values():
            for sc, tname in cg.subject_teacher_map.items():
                if sc in subjects and tname in teacher_loads:
                    teacher_loads[tname] += subjects[sc].weekly_hours

        # Assign remaining
        for cg in classes.values():
            for sc in cg.subjects:
                if sc not in cg.subject_teacher_map or not cg.subject_teacher_map[sc]:
                    needed_hours = subjects[sc].weekly_hours if sc in subjects else 3
                    # Find eligible teachers
                    eligible = [
                        tname for tname, t in teachers.items()
                        if sc in t.subjects and (teacher_loads[tname] + needed_hours <= t.max_weekly_load)
                    ]
                    if not eligible:
                        # Fallback to any teacher who can teach it
                        eligible = [tname for tname, t in teachers.items() if sc in t.subjects]

                    if eligible:
                        # Pick least loaded
                        best_teacher = min(eligible, key=lambda tname: teacher_loads[tname])
                        cg.subject_teacher_map[sc] = best_teacher
                        teacher_loads[best_teacher] += needed_hours
                    else:
                        raise DataValidationError(f"No eligible teacher found for subject {sc} in class {cg.name}")

    @staticmethod
    def validate_dataset(subjects: Dict[str, Subject], teachers: Dict[str, Teacher],
                         rooms: Dict[str, Room], classes: Dict[str, ClassGroup],
                         time_structure: TimeStructure) -> List[str]:
        """
        Validates data consistency and performs mathematical solvability checks.
        Returns a list of warning/error messages (empty if completely clean).
        """
        errors = []
        days_count = len(time_structure.working_days)
        slots_per_day = time_structure.periods_per_day - len(time_structure.break_periods)
        total_slots_per_room = days_count * slots_per_day

        # Check classes and subjects
        for cname, cg in classes.items():
            class_total_hours = 0
            for sc in cg.subjects:
                if sc not in subjects:
                    errors.append(f"Class '{cname}' references undefined subject code '{sc}'.")
                else:
                    class_total_hours += subjects[sc].weekly_hours
            if class_total_hours > days_count * slots_per_day:
                errors.append(f"Class '{cname}' requires {class_total_hours} weekly hours, but only {days_count * slots_per_day} non-break periods exist per week.")

        # Check rooms and capacities
        theory_rooms = [r for r in rooms.values() if r.type == 'classroom']
        lab_rooms = [r for r in rooms.values() if r.type == 'lab']

        if not theory_rooms:
            errors.append("No classroom rooms defined!")
        if not lab_rooms:
            errors.append("No lab rooms defined!")

        total_theory_slots = len(theory_rooms) * total_slots_per_room
        total_lab_slots = len(lab_rooms) * total_slots_per_room

        total_required_theory_hours = 0
        total_required_lab_hours = 0

        for cg in classes.values():
            for sc in cg.subjects:
                if sc in subjects:
                    sub = subjects[sc]
                    if sub.type == 'lab':
                        total_required_lab_hours += sub.weekly_hours
                    else:
                        total_required_theory_hours += sub.weekly_hours

        if total_required_theory_hours > total_theory_slots:
            errors.append(f"Total theory hours ({total_required_theory_hours}) exceeds available classroom slots ({total_theory_slots}). Infeasible!")
        if total_required_lab_hours > total_lab_slots:
            errors.append(f"Total lab hours ({total_required_lab_hours}) exceeds available lab slots ({total_lab_slots}). Infeasible!")

        # Check teacher loads
        teacher_assigned_hours = {tname: 0 for tname in teachers}
        for cg in classes.values():
            for sc in cg.subjects:
                tname = cg.subject_teacher_map.get(sc)
                if tname:
                    if tname not in teachers:
                        errors.append(f"Class '{cg.name}' assigns unknown teacher '{tname}' to subject '{sc}'.")
                    else:
                        if sc in subjects:
                            teacher_assigned_hours[tname] += subjects[sc].weekly_hours

        for tname, assigned in teacher_assigned_hours.items():
            t = teachers[tname]
            if assigned > t.max_weekly_load:
                errors.append(f"Teacher '{tname}' is assigned {assigned} hours, exceeding max weekly load of {t.max_weekly_load} (H8 violation).")

        return errors

    @staticmethod
    def generate_sessions(classes: Dict[str, ClassGroup], subjects: Dict[str, Subject], teachers: Dict[str, Teacher]) -> List[Session]:
        """
        Converts weekly curriculum requirements into discrete CSP Session variables.
        Lab hours are grouped into 2-period atomic blocks (satisfying S3 consecutively).
        Theory hours are individual 1-period sessions.
        """
        sessions = []
        for cname, cg in classes.items():
            for sc in cg.subjects:
                sub = subjects[sc]
                tname = cg.subject_teacher_map.get(sc, "")
                hours = sub.weekly_hours

                if sub.type == 'lab':
                    # Group into 2-hour blocks
                    session_idx = 1
                    while hours >= 2:
                        sess_id = f"{cname}_{sc}_lab_blk{session_idx}"
                        sessions.append(Session(
                            id=sess_id,
                            class_name=cname,
                            subject_code=sc,
                            teacher_name=tname,
                            session_type='lab',
                            duration=2,
                            session_index=session_idx
                        ))
                        hours -= 2
                        session_idx += 1
                    if hours == 1:
                        # 1 remaining lab hour
                        sess_id = f"{cname}_{sc}_lab_blk{session_idx}"
                        sessions.append(Session(
                            id=sess_id,
                            class_name=cname,
                            subject_code=sc,
                            teacher_name=tname,
                            session_type='lab',
                            duration=1,
                            session_index=session_idx
                        ))
                else:
                    # Single 1-hour theory sessions
                    for i in range(1, hours + 1):
                        sess_id = f"{cname}_{sc}_lec{i}"
                        sessions.append(Session(
                            id=sess_id,
                            class_name=cname,
                            subject_code=sc,
                            teacher_name=tname,
                            session_type='theory',
                            duration=1,
                            session_index=i
                        ))
        return sessions

    @staticmethod
    def generate_domains(sessions: List[Session], rooms: Dict[str, Room],
                         time_structure: TimeStructure, teachers: Dict[str, Teacher],
                         classes: Dict[str, ClassGroup]) -> Dict[Session, List[SessionPlacement]]:
        """
        Constructs unary-filtered domains for all session variables:
        - Room type match (lab in lab, theory in classroom)
        - Room capacity >= class strength
        - No placement overlapping class lunch break
        - Teacher availability respect
        - Fits within day bounds (for duration 2)
        """
        domains: Dict[Session, List[SessionPlacement]] = {}
        for session in sessions:
            cg = classes[session.class_name]
            class_strength = cg.strength
            lunch_slot = cg.lunch_break_slot
            teacher = teachers.get(session.teacher_name)
            unavail_slots = set(teacher.unavailable_slots) if teacher else set()

            valid_placements = []
            for rname, room in rooms.items():
                # H4: Room capacity
                if room.capacity < class_strength:
                    continue
                # H5: Room type match
                if session.session_type == 'lab' and room.type != 'lab':
                    continue
                if session.session_type == 'theory' and room.type != 'classroom':
                    continue

                for day in time_structure.working_days:
                    for period in range(1, time_structure.periods_per_day + 1):
                        # For duration, check that it fits in day
                        if period + session.duration - 1 > time_structure.periods_per_day:
                            continue

                        # Check lunch conflict for all covered periods (H9)
                        covered_periods = [period + i for i in range(session.duration)]
                        if lunch_slot in covered_periods:
                            continue

                        # Check teacher availability (H6)
                        teacher_clash = any((day, p) in unavail_slots for p in covered_periods)
                        if teacher_clash:
                            continue

                        valid_placements.append(SessionPlacement(day=day, period=period, room=rname))

            domains[session] = valid_placements
        return domains
