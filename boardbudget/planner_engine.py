from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from math import isfinite

from .config import DEFAULT_HOURS_PER_DAY, DEFAULT_MAX_CALENDAR_DAYS, STATUS_PLANNED, WEEKDAY_CODES
from .models import Activity, BoardData, CalendarAllocation, Person, WarningMessage
from .validation import validate_board_data


@dataclass
class PlanningResult:
    allocations: list[CalendarAllocation] = field(default_factory=list)
    warnings: list[WarningMessage] = field(default_factory=list)
    activity_summary: list[dict[str, object]] = field(default_factory=list)
    person_summary: list[dict[str, object]] = field(default_factory=list)


def _positive_or_default(value: object, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not isfinite(number) or number <= 0:
        return default
    return number


def _activity_order(activity: Activity) -> tuple[int, str]:
    return (activity.order if activity.order is not None else 999_999_999, activity.activity_id)


def _is_working_day(day: date, working_days: tuple[str, ...]) -> bool:
    allowed = {WEEKDAY_CODES[d] for d in working_days if d in WEEKDAY_CODES}
    if not allowed:
        allowed = {0, 1, 2, 3, 4}
    return day.weekday() in allowed


def _dedup_warnings(warnings: list[WarningMessage]) -> list[WarningMessage]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[WarningMessage] = []
    for warning in warnings:
        key = (warning.level, warning.code, warning.message)
        if key not in seen:
            unique.append(warning)
            seen.add(key)
    return unique


def calculate_plan(board_data: BoardData, today: date | None = None) -> PlanningResult:
    warnings = list(board_data.warnings) + validate_board_data(board_data)
    people_by_id: dict[str, Person] = {p.person_id: p for p in board_data.people if p.person_id and p.active}
    activities_by_id: dict[str, Activity] = {a.activity_id: a for a in board_data.activities if a.activity_id}

    assignment_map: dict[str, list[str]] = {}
    seen_assignments: set[tuple[str, str]] = set()
    for assignment in board_data.assignments:
        pair = (assignment.activity_id, assignment.person_id)
        if pair in seen_assignments:
            continue
        seen_assignments.add(pair)
        if assignment.activity_id in activities_by_id and assignment.person_id in people_by_id:
            assignment_map.setdefault(assignment.activity_id, []).append(assignment.person_id)

    planned_activities: list[Activity] = []
    quotas: dict[tuple[str, str], float] = {}
    remaining: dict[tuple[str, str], float] = {}
    for activity in board_data.activities:
        if not activity.activity_id:
            continue
        status = activity.status if activity.status in ("PLANNED", "DONE", "CANCELLED") else STATUS_PLANNED
        estimated_hours = _positive_or_default(activity.estimated_hours, 0)
        assignees = assignment_map.get(activity.activity_id, [])
        if status != STATUS_PLANNED or estimated_hours <= 0 or not assignees:
            continue
        planned_activities.append(activity)
        quota = estimated_hours / len(assignees)
        for person_id in assignees:
            quotas[(person_id, activity.activity_id)] = quota
            remaining[(person_id, activity.activity_id)] = quota

    planned_activities.sort(key=_activity_order)
    allocations: list[CalendarAllocation] = []
    daily_activity_hours: dict[tuple[date, str, str], float] = {}

    current_day = board_data.settings.start_date
    last_day = board_data.settings.start_date + timedelta(days=DEFAULT_MAX_CALENDAR_DAYS - 1)
    while current_day <= last_day and any(hours > 0.000001 for hours in remaining.values()):
        if not _is_working_day(current_day, board_data.settings.working_days):
            current_day += timedelta(days=1)
            continue

        for person in sorted(people_by_id.values(), key=lambda p: p.person_id):
            daily_remaining = _positive_or_default(person.hours_per_day, board_data.settings.hours_per_day)
            while daily_remaining > 0.000001:
                selected: Activity | None = None
                selected_remaining_max = 0.0
                for activity in planned_activities:
                    key = (person.person_id, activity.activity_id)
                    if remaining.get(key, 0.0) <= 0.000001:
                        continue
                    max_per_day = _positive_or_default(activity.max_hours_per_day, DEFAULT_HOURS_PER_DAY)
                    used_today = daily_activity_hours.get((current_day, person.person_id, activity.activity_id), 0.0)
                    remaining_max = max_per_day - used_today
                    if remaining_max > 0.000001:
                        selected = activity
                        selected_remaining_max = remaining_max
                        break

                if selected is None:
                    break

                key = (person.person_id, selected.activity_id)
                hours = min(daily_remaining, remaining[key], selected_remaining_max)
                hours = round(hours, 6)
                if hours <= 0:
                    break

                allocations.append(
                    CalendarAllocation(
                        date=current_day,
                        person_id=person.person_id,
                        person_name=person.name,
                        activity_id=selected.activity_id,
                        activity_name=selected.name,
                        hours=hours,
                    )
                )
                daily_activity_hours[(current_day, person.person_id, selected.activity_id)] = (
                    daily_activity_hours.get((current_day, person.person_id, selected.activity_id), 0.0) + hours
                )
                remaining[key] = round(remaining[key] - hours, 6)
                daily_remaining = round(daily_remaining - hours, 6)

        current_day += timedelta(days=1)

    if any(hours > 0.000001 for hours in remaining.values()):
        warnings.append(
            WarningMessage(
                "ERROR",
                "PLANNING_DID_NOT_FINISH",
                f"Planning did not finish within {DEFAULT_MAX_CALENDAR_DAYS} calendar days.",
            )
        )

    activity_summary = []
    for activity in sorted(planned_activities, key=_activity_order):
        allocated = sum(a.hours for a in allocations if a.activity_id == activity.activity_id)
        activity_summary.append(
            {
                "activity_id": activity.activity_id,
                "activity_name": activity.name,
                "estimated_hours": float(activity.estimated_hours),
                "allocated_hours": round(allocated, 2),
                "remaining_hours": round(max(float(activity.estimated_hours) - allocated, 0), 2),
            }
        )

    person_summary = []
    for person in sorted(people_by_id.values(), key=lambda p: p.person_id):
        person_allocations = [a for a in allocations if a.person_id == person.person_id]
        total = sum(a.hours for a in person_allocations)
        last = max((a.date for a in person_allocations), default=None)
        person_summary.append(
            {
                "person_id": person.person_id,
                "person_name": person.name,
                "total_allocated_hours": round(total, 2),
                "allocated_until": last,
            }
        )

    return PlanningResult(
        allocations=allocations,
        warnings=_dedup_warnings(warnings),
        activity_summary=activity_summary,
        person_summary=person_summary,
    )

