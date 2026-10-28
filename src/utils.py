"""
Utility and export functions for AI Timetable Scheduler:
- Grid view formatting (By Class, By Teacher, By Room)
- CSV and Excel multi-tab export (openpyxl)
- Timetable summary helpers
"""
import io
import csv
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from .models import Session, SessionPlacement, Room, Teacher, ClassGroup, TimeStructure, Subject

def build_grid_by_class(assignment: Dict[Session, SessionPlacement],
                        class_name: str,
                        time_structure: TimeStructure,
                        classes: Dict[str, ClassGroup]) -> pd.DataFrame:
    """
    Constructs a DataFrame for a specific class:
    Rows = Working Days, Columns = Periods 1 to N.
    """
    lunch_slot = classes[class_name].lunch_break_slot if class_name in classes else 4
    cols = [f"Period {p}" for p in range(1, time_structure.periods_per_day + 1)]
    df = pd.DataFrame("", index=time_structure.working_days, columns=cols)

    # Mark lunch break
    if 1 <= lunch_slot <= time_structure.periods_per_day:
        df[f"Period {lunch_slot}"] = "[ LUNCH BREAK ]"

    for session, placement in assignment.items():
        if placement is None or session.class_name != class_name:
            continue

        for i in range(session.duration):
            p = placement.period + i
            if 1 <= p <= time_structure.periods_per_day:
                cell_val = f"{session.subject_code} | {session.teacher_name} ({placement.room})"
                if session.session_type == 'lab':
                    cell_val = f"[LAB] {cell_val}"
                df.at[placement.day, f"Period {p}"] = cell_val

    return df

def build_grid_by_teacher(assignment: Dict[Session, SessionPlacement],
                          teacher_name: str,
                          time_structure: TimeStructure) -> pd.DataFrame:
    """
    Constructs a DataFrame for a specific teacher:
    Rows = Working Days, Columns = Periods 1 to N.
    """
    cols = [f"Period {p}" for p in range(1, time_structure.periods_per_day + 1)]
    df = pd.DataFrame("", index=time_structure.working_days, columns=cols)

    for session, placement in assignment.items():
        if placement is None or session.teacher_name != teacher_name:
            continue

        for i in range(session.duration):
            p = placement.period + i
            if 1 <= p <= time_structure.periods_per_day:
                cell_val = f"{session.class_name} | {session.subject_code} ({placement.room})"
                df.at[placement.day, f"Period {p}"] = cell_val

    return df

def build_grid_by_room(assignment: Dict[Session, SessionPlacement],
                       room_name: str,
                       time_structure: TimeStructure) -> pd.DataFrame:
    """
    Constructs a DataFrame for a specific room:
    Rows = Working Days, Columns = Periods 1 to N.
    """
    cols = [f"Period {p}" for p in range(1, time_structure.periods_per_day + 1)]
    df = pd.DataFrame("", index=time_structure.working_days, columns=cols)

    for session, placement in assignment.items():
        if placement is None or placement.room != room_name:
            continue

        for i in range(session.duration):
            p = placement.period + i
            if 1 <= p <= time_structure.periods_per_day:
                cell_val = f"{session.class_name} | {session.subject_code} | {session.teacher_name}"
                df.at[placement.day, f"Period {p}"] = cell_val

    return df

def get_tabular_data(assignment: Dict[Session, SessionPlacement]) -> List[Dict[str, Any]]:
    """Converts the raw assignment to a flat list of records."""
    records = []
    for session, placement in sorted(assignment.items(), key=lambda item: (item[0].class_name, item[1].day if item[1] else "", item[1].period if item[1] else 0)):
        if placement is None:
            continue
        for i in range(session.duration):
            records.append({
                "Class": session.class_name,
                "Day": placement.day,
                "Period": placement.period + i,
                "Subject Code": session.subject_code,
                "Session Type": session.session_type.capitalize(),
                "Teacher": session.teacher_name,
                "Room": placement.room,
                "Session ID": session.id
            })
    return records

def export_to_csv_string(assignment: Dict[Session, SessionPlacement]) -> str:
    """Returns CSV string of flat timetable records."""
    records = get_tabular_data(assignment)
    if not records:
        return ""
    df = pd.DataFrame(records)
    return df.to_csv(index=False)

def export_to_excel_bytes(assignment: Dict[Session, SessionPlacement],
                          classes: Dict[str, ClassGroup],
                          teachers: Dict[str, Teacher],
                          rooms: Dict[str, Room],
                          time_structure: TimeStructure) -> bytes:
    """
    Exports a styled Excel workbook with multiple tabs:
    - Master Schedule (Flat table)
    - Grids by Class
    - Grids by Teacher
    - Grids by Room
    """
    wb = openpyxl.Workbook()
    # Sheet 1: Master
    ws_master = wb.active
    ws_master.title = "Master Schedule"

    records = get_tabular_data(assignment)
    headers = ["Class", "Day", "Period", "Subject Code", "Session Type", "Teacher", "Room", "Session ID"]
    ws_master.append(headers)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")

    for col_num, header in enumerate(headers, 1):
        cell = ws_master.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for rec in records:
        ws_master.append([
            rec["Class"], rec["Day"], rec["Period"], rec["Subject Code"],
            rec["Session Type"], rec["Teacher"], rec["Room"], rec["Session ID"]
        ])

    # Sheet 2: Class Grids
    ws_classes = wb.create_sheet(title="By Class")
    row_idx = 1
    for cname in sorted(classes.keys()):
        ws_classes.cell(row=row_idx, column=1, value=f"Class Timetable: {cname}").font = Font(size=13, bold=True, color="1F497D")
        row_idx += 1
        df_c = build_grid_by_class(assignment, cname, time_structure, classes)

        # Header row
        ws_classes.cell(row=row_idx, column=1, value="Day").font = header_font
        ws_classes.cell(row=row_idx, column=1).fill = header_fill
        for col_idx, col_name in enumerate(df_c.columns, 2):
            cell = ws_classes.cell(row=row_idx, column=col_idx, value=col_name)
            cell.font = header_font
            cell.fill = header_fill
        row_idx += 1

        for day in df_c.index:
            ws_classes.cell(row=row_idx, column=1, value=day).font = Font(bold=True)
            for col_idx, col_name in enumerate(df_c.columns, 2):
                val = df_c.at[day, col_name]
                ws_classes.cell(row=row_idx, column=col_idx, value=val)
            row_idx += 1
        row_idx += 2

    # Auto-adjust column widths
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
