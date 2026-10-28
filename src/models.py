"""
Core Data Models for AI Timetable Scheduler
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

@dataclass
class Subject:
    code: str
    name: str
    weekly_hours: int
    type: str  # 'theory' or 'lab'

@dataclass
class Teacher:
    name: str
    subjects: List[str]
    unavailable_slots: List[Tuple[str, int]] = field(default_factory=list)  # (day, period)
    max_weekly_load: int = 20
    preferences: Dict[str, Any] = field(default_factory=dict)  # e.g., {"avoid_first_period": True, "preferred_days": [...]}

@dataclass
class ClassGroup:
    name: str
    strength: int
    subjects: List[str]  # subject codes
    lunch_break_slot: int = 4  # 1-indexed period (e.g., period 4)
    subject_teacher_map: Dict[str, str] = field(default_factory=dict)  # subject_code -> teacher_name

@dataclass
class Room:
    name: str
    capacity: int
    type: str  # 'classroom' or 'lab'

@dataclass
class TimeStructure:
    working_days: List[str] = field(default_factory=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    periods_per_day: int = 6
    break_periods: List[int] = field(default_factory=lambda: [4])  # 1-indexed periods reserved for lunch/break

@dataclass
class Session:
    """
    Represents an atomic variable in the CSP.
    For theory: duration = 1.
    For lab: duration = 2 (consecutive block as required by hard constraint).
    """
    id: str
    class_name: str
    subject_code: str
    teacher_name: str
    session_type: str  # 'theory' or 'lab'
    duration: int = 1
    session_index: int = 1

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Session):
            return False
        return self.id == other.id

@dataclass
class Slot:
    """A specific time slot."""
    day: str
    period: int  # 1-indexed

    def __hash__(self):
        return hash((self.day, self.period))

    def __eq__(self, other):
        if not isinstance(other, Slot):
            return False
        return self.day == other.day and self.period == other.period

@dataclass
class SessionPlacement:
    """The value assigned to a Session variable."""
    day: str
    period: int  # 1-indexed start period
    room: str

    def get_occupied_slots(self, duration: int) -> List[Tuple[str, int]]:
        """Returns all (day, period) slots covered by this placement."""
        return [(self.day, self.period + i) for i in range(duration)]

    def __hash__(self):
        return hash((self.day, self.period, self.room))

    def __eq__(self, other):
        if not isinstance(other, SessionPlacement):
            return False
        return self.day == other.day and self.period == other.period and self.room == other.room
