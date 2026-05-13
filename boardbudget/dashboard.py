from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from .config import WEEKDAY_CODES
from .models import BoardData, WarningMessage
from .planner_engine import PlanningResult


def _is_working_day(day: date, working_days: tuple[str, ...]) -> bool:
    allowed = {WEEKDAY_CODES[d] for d in working_days if d in WEEKDAY_CODES} or {0, 1, 2, 3, 4}
    return day.weekday() in allowed


def _next_working_day(day: date, working_days: tuple[str, ...]) -> date:
    current = day + timedelta(days=1)
    while not _is_working_day(current, working_days):
        current += timedelta(days=1)
    return current


def _working_days_between(start: date | None, end: date | None, working_days: tuple[str, ...]) -> int:
    if start is None or end is None or end < start:
        return 0
    count = 0
    current = start
    while current <= end:
        if _is_working_day(current, working_days):
            count += 1
        current += timedelta(days=1)
    return count


def build_calendar_dataframe(result: PlanningResult, board_data: BoardData) -> pd.DataFrame:
    rows = [
        {
            "date": allocation.date.isoformat(),
            "person_id": allocation.person_id,
            "person_name": allocation.person_name,
            "activity_id": allocation.activity_id,
            "activity_name": allocation.activity_name,
            "hours": allocation.hours,
        }
        for allocation in result.allocations
    ]
    return pd.DataFrame(rows, columns=["date", "person_id", "person_name", "activity_id", "activity_name", "hours"])


def build_calendar_pivot_dataframe(calendar_df: pd.DataFrame) -> pd.DataFrame:
    if calendar_df.empty:
        return pd.DataFrame(columns=["date"])

    work = calendar_df.copy()
    work["entry"] = work.apply(lambda r: f"{r['activity_id']} {r['activity_name']} {r['hours']:g}h", axis=1)
    grouped = (
        work.groupby(["date", "person_id"], sort=True)["entry"]
        .apply(lambda values: " + ".join(values))
        .reset_index()
    )
    pivot = grouped.pivot(index="date", columns="person_id", values="entry").fillna("").reset_index()
    pivot.columns.name = None
    return pivot


def build_dashboard_dataframe(result: PlanningResult, board_data: BoardData, today: date | None = None) -> pd.DataFrame:
    today = today or date.today()
    allocations = result.allocations
    planned_start = min((a.date for a in allocations), default=None)
    planned_end = max((a.date for a in allocations), default=None)
    total_allocated = sum(a.hours for a in allocations)
    team_capacity = sum((p.hours_per_day or board_data.settings.hours_per_day) for p in board_data.people if p.active)
    remaining_from_today = sum(a.hours for a in allocations if a.date >= today)
    working_days = _working_days_between(planned_start, planned_end, board_data.settings.working_days)

    metrics: list[tuple[str, object]] = [
        ("board_name", board_data.settings.board_name),
        ("start_date", board_data.settings.start_date.isoformat()),
        ("total_estimated_hours_planned", round(total_allocated, 2)),
        ("total_estimated_person_days_planned", round(total_allocated / board_data.settings.hours_per_day, 2) if board_data.settings.hours_per_day else 0),
        ("team_daily_capacity_hours", round(team_capacity, 2)),
        ("planned_start_date", planned_start.isoformat() if planned_start else ""),
        ("planned_end_date", planned_end.isoformat() if planned_end else ""),
        ("total_calendar_days", (planned_end - planned_start).days + 1 if planned_start and planned_end else 0),
        ("total_working_days", working_days),
        ("total_allocated_hours", round(total_allocated, 2)),
        ("remaining_hours_from_today", round(remaining_from_today, 2)),
        ("remaining_person_days_from_today", round(remaining_from_today / board_data.settings.hours_per_day, 2) if board_data.settings.hours_per_day else 0),
        ("if_finished_today.remaining_allocated_hours", round(remaining_from_today, 2)),
        ("if_finished_today.remaining_person_days", round(remaining_from_today / board_data.settings.hours_per_day, 2) if board_data.settings.hours_per_day else 0),
        ("if_finished_today.remaining_calendar_days_until_planned_end", (planned_end - today).days if planned_end and planned_end >= today else 0),
    ]

    for person in sorted([p for p in board_data.people if p.active], key=lambda p: p.person_id):
        person_allocations = [a for a in allocations if a.person_id == person.person_id]
        last = max((a.date for a in person_allocations), default=None)
        total = sum(a.hours for a in person_allocations)
        metrics.extend(
            [
                (f"person.{person.person_id}.allocated_until", last.isoformat() if last else ""),
                (f"person.{person.person_id}.total_allocated_hours", round(total, 2)),
                (f"person.{person.person_id}.first_free_working_day_after_plan", _next_working_day(last, board_data.settings.working_days).isoformat() if last else board_data.settings.start_date.isoformat()),
            ]
        )

    return pd.DataFrame(metrics, columns=["metric", "value"])


def build_warnings_dataframe(warnings: list[WarningMessage]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"level": w.level, "code": w.code, "message": w.message} for w in warnings],
        columns=["level", "code", "message"],
    )


def build_activity_summary_dataframe(result: PlanningResult, board_data: BoardData) -> pd.DataFrame:
    return pd.DataFrame(result.activity_summary)


def build_person_summary_dataframe(result: PlanningResult, board_data: BoardData) -> pd.DataFrame:
    return pd.DataFrame(result.person_summary)

