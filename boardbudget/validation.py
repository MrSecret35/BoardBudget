from __future__ import annotations

from datetime import date
from math import isfinite
from typing import Iterable

from .config import ALLOWED_STATUSES
from .models import BoardData, WarningMessage


def _is_blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def _is_positive_number(value: object) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return isfinite(number) and number > 0


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return dupes


def validate_board_data(board_data: BoardData) -> list[WarningMessage]:
    warnings: list[WarningMessage] = []

    if not isinstance(board_data.settings.start_date, date):
        warnings.append(WarningMessage("ERROR", "INVALID_START_DATE", "Board start_date must be a valid date."))

    person_ids = [p.person_id.strip() for p in board_data.people if not _is_blank(p.person_id)]
    missing_person_rows = [idx + 2 for idx, p in enumerate(board_data.people) if _is_blank(p.person_id)]
    for row in missing_person_rows:
        warnings.append(WarningMessage("ERROR", "MISSING_PERSON_ID", f"Person row {row} is missing person_id."))

    for person_id in sorted(_duplicates(person_ids)):
        warnings.append(WarningMessage("ERROR", "DUPLICATE_PERSON_ID", f"Person id '{person_id}' appears more than once."))

    for person in board_data.people:
        if _is_blank(person.name):
            warnings.append(WarningMessage("ERROR", "MISSING_PERSON_NAME", f"Person '{person.person_id}' is missing name."))
        if person.hours_per_day is not None and not _is_positive_number(person.hours_per_day):
            warnings.append(
                WarningMessage("WARNING", "INVALID_PERSON_HOURS", f"Person '{person.person_id}' has invalid hours_per_day; board default will be used.")
            )
        if person.active and not _is_positive_number(person.daily_cost):
            warnings.append(
                WarningMessage(
                    "WARNING",
                    "MISSING_DAILY_COST",
                    f"Person {person.person_id} has no valid daily_cost; delivery cost defaults to 0.",
                )
            )

    activity_ids = [a.activity_id.strip() for a in board_data.activities if not _is_blank(a.activity_id)]
    for idx, activity in enumerate(board_data.activities, start=2):
        if _is_blank(activity.activity_id):
            warnings.append(WarningMessage("ERROR", "MISSING_ACTIVITY_ID", f"Activity row {idx} is missing activity_id."))

    for activity_id in sorted(_duplicates(activity_ids)):
        warnings.append(WarningMessage("ERROR", "DUPLICATE_ACTIVITY_ID", f"Activity id '{activity_id}' appears more than once."))

    for activity in board_data.activities:
        label = activity.activity_id or activity.name or "<blank>"
        if _is_blank(activity.name):
            warnings.append(WarningMessage("ERROR", "MISSING_ACTIVITY_NAME", f"Activity '{label}' is missing name."))
        if not _is_positive_number(activity.estimated_hours):
            warnings.append(WarningMessage("WARNING", "INVALID_ESTIMATED_HOURS", f"Activity '{label}' has estimated_hours <= 0 and will not be planned."))
        if activity.order is None:
            warnings.append(WarningMessage("WARNING", "MISSING_ORDER", f"Activity '{label}' has no order; it will be planned after ordered activities."))
        if activity.status not in ALLOWED_STATUSES:
            warnings.append(WarningMessage("WARNING", "INVALID_STATUS", f"Activity '{label}' has invalid status '{activity.status}'; PLANNED will be used."))
        if activity.max_hours_per_day is not None and not _is_positive_number(activity.max_hours_per_day):
            warnings.append(WarningMessage("WARNING", "INVALID_MAX_HOURS", f"Activity '{label}' has invalid max_hours_per_day; 8 will be used."))
        if activity.estimated_days is not None and _is_positive_number(activity.estimated_days) and _is_positive_number(activity.estimated_hours):
            if abs(float(activity.estimated_days) * 8 - float(activity.estimated_hours)) > 0.000001:
                warnings.append(
                    WarningMessage(
                        "WARNING",
                        "ESTIMATE_DAYS_HOURS_MISMATCH",
                        f"Activity {label} has estimated_days and estimated_hours inconsistent; estimated_hours was used.",
                    )
                )
        if activity.status == "PLANNED" and not _is_positive_number(activity.daily_price):
            warnings.append(
                WarningMessage(
                    "WARNING",
                    "MISSING_DAILY_PRICE",
                    f"Activity {label} has no valid daily_price; economic value defaults to 0.",
                )
            )

    activity_id_set = set(activity_ids)
    active_person_ids = {p.person_id.strip() for p in board_data.people if not _is_blank(p.person_id) and p.active}
    all_person_ids = set(person_ids)
    assignment_pairs: list[tuple[str, str]] = []

    for assignment in board_data.assignments:
        activity_id = assignment.activity_id.strip()
        person_id = assignment.person_id.strip()
        assignment_pairs.append((activity_id, person_id))
        if activity_id not in activity_id_set:
            warnings.append(WarningMessage("ERROR", "ASSIGNMENT_UNKNOWN_ACTIVITY", f"Assignment references missing activity '{activity_id}'."))
        if person_id not in all_person_ids:
            warnings.append(WarningMessage("ERROR", "ASSIGNMENT_UNKNOWN_PERSON", f"Assignment references missing person '{person_id}'."))
        elif person_id not in active_person_ids:
            warnings.append(WarningMessage("WARNING", "ASSIGNMENT_INACTIVE_PERSON", f"Assignment references inactive person '{person_id}' and will be ignored."))

    for pair in sorted(_duplicates([f"{a}|{p}" for a, p in assignment_pairs])):
        activity_id, person_id = pair.split("|", 1)
        warnings.append(WarningMessage("WARNING", "DUPLICATE_ASSIGNMENT", f"Duplicate assignment '{activity_id}' -> '{person_id}' will be ignored."))

    assigned_activity_ids = {a for a, p in assignment_pairs if a in activity_id_set and p in active_person_ids}
    for activity in board_data.activities:
        status = activity.status if activity.status in ALLOWED_STATUSES else "PLANNED"
        if status == "PLANNED" and activity.activity_id not in assigned_activity_ids:
            warnings.append(WarningMessage("WARNING", "ACTIVITY_WITHOUT_ASSIGNMENT", f"Activity '{activity.activity_id}' has no active assignments and will not be planned."))

    return warnings
