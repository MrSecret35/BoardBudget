from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from .calendar_utils import classify_day, get_italian_holidays_for_years, is_non_working_day
from .config import STATUS_PLANNED
from .config import WEEKDAY_CODES
from .models import BoardData, WarningMessage
from .planner_engine import PlanningResult


def _is_working_day(day: date, working_days: tuple[str, ...], holidays_map: dict[date, str] | None = None) -> bool:
    if holidays_map is not None and is_non_working_day(day, holidays_map):
        return False
    allowed = {WEEKDAY_CODES[d] for d in working_days if d in WEEKDAY_CODES} or {0, 1, 2, 3, 4}
    return day.weekday() in allowed


def _next_working_day(day: date, working_days: tuple[str, ...]) -> date:
    holidays_map = get_italian_holidays_for_years({day.year, (day + timedelta(days=370)).year})
    current = day + timedelta(days=1)
    while not _is_working_day(current, working_days, holidays_map):
        current += timedelta(days=1)
    return current


def _working_days_between(start: date | None, end: date | None, working_days: tuple[str, ...]) -> int:
    if start is None or end is None or end < start:
        return 0
    holidays_map = get_italian_holidays_for_years(set(range(start.year, end.year + 1)))
    count = 0
    current = start
    while current <= end:
        if _is_working_day(current, working_days, holidays_map):
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


def build_calendar_pivot_dataframe(calendar_df: pd.DataFrame, board_data: BoardData | None = None) -> pd.DataFrame:
    person_ids = [p.person_id for p in board_data.people if p.active] if board_data else []
    if calendar_df.empty:
        return pd.DataFrame(columns=["date", "day_name", "day_type", "holiday_name", *person_ids])

    work = calendar_df.copy()
    work["date"] = pd.to_datetime(work["date"]).dt.date
    person_ids = person_ids or sorted(work["person_id"].dropna().unique().tolist())
    start = min(work["date"])
    end = max(work["date"])
    all_dates = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
    holidays_map = get_italian_holidays_for_years({day.year for day in all_dates})

    work["entry"] = work.apply(lambda r: f"{r['activity_id']} {r['activity_name']} {r['hours']:g}h", axis=1)
    grouped = (
        work.groupby(["date", "person_id"], sort=True)["entry"]
        .apply(lambda values: " + ".join(values))
        .reset_index()
    )

    rows: list[dict[str, object]] = []
    for day in all_dates:
        day_type, holiday_name = classify_day(day, holidays_map)
        row: dict[str, object] = {
            "date": day.isoformat(),
            "day_name": day.strftime("%A"),
            "day_type": day_type,
            "holiday_name": holiday_name,
        }
        for person_id in person_ids:
            match = grouped[(grouped["date"] == day) & (grouped["person_id"] == person_id)]
            row[person_id] = "" if match.empty else match.iloc[0]["entry"]
        rows.append(row)
    return pd.DataFrame(rows, columns=["date", "day_name", "day_type", "holiday_name", *person_ids])


def build_dashboard_dataframe(result: PlanningResult, board_data: BoardData, today: date | None = None) -> pd.DataFrame:
    today = today or date.today()
    allocations = result.allocations
    planned_start = min((a.date for a in allocations), default=None)
    planned_end = max((a.date for a in allocations), default=None)
    total_allocated = sum(a.hours for a in allocations)
    team_capacity = sum((p.hours_per_day or board_data.settings.hours_per_day) for p in board_data.people if p.active)
    remaining_from_today = sum(a.hours for a in allocations if a.date >= today)
    working_days = _working_days_between(planned_start, planned_end, board_data.settings.working_days)
    economics_df = build_activity_economics_dataframe(result, board_data, today)
    person_economics_df = build_person_economics_dataframe(result, board_data, today)
    total_estimated_value = economics_df["estimated_value"].sum() if not economics_df.empty else 0
    total_allocated_value = economics_df["allocated_value"].sum() if not economics_df.empty else 0
    remaining_allocated_value = economics_df["remaining_allocated_value_from_today"].sum() if not economics_df.empty else 0
    delivered_value = economics_df["delivered_value_until_today"].sum() if not economics_df.empty else 0
    delivered_cost = person_economics_df["delivered_cost_until_today"].sum() if not person_economics_df.empty else 0
    estimated_delivery_cost = person_economics_df["estimated_delivery_cost"].sum() if not person_economics_df.empty else 0
    remaining_delivery_cost = person_economics_df["remaining_delivery_cost_from_today"].sum() if not person_economics_df.empty else 0
    expected_margin = total_estimated_value - estimated_delivery_cost
    expected_margin_percentage = (expected_margin / total_estimated_value * 100) if total_estimated_value else 0
    delivered_margin = delivered_value - delivered_cost
    remaining_margin = remaining_allocated_value - remaining_delivery_cost
    total_estimated_person_days = economics_df["estimated_person_days"].sum() if not economics_df.empty else 0
    average_daily_price = total_estimated_value / total_estimated_person_days if total_estimated_person_days else 0

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
        ("total_estimated_value", round(total_estimated_value, 2)),
        ("total_allocated_value", round(total_allocated_value, 2)),
        ("remaining_allocated_value_from_today", round(remaining_allocated_value, 2)),
        ("average_daily_price_weighted", round(average_daily_price, 2)),
        ("value_until_planned_end", round(total_allocated_value, 2)),
        ("delivered_cost_until_today", round(delivered_cost, 2)),
        ("estimated_delivery_cost", round(estimated_delivery_cost, 2)),
        ("remaining_delivery_cost_from_today", round(remaining_delivery_cost, 2)),
        ("expected_margin", round(expected_margin, 2)),
        ("expected_margin_percentage", round(expected_margin_percentage, 2)),
        ("delivered_margin_until_today", round(delivered_margin, 2)),
        ("remaining_margin_from_today", round(remaining_margin, 2)),
        ("if_finished_today.remaining_allocated_hours", round(remaining_from_today, 2)),
        ("if_finished_today.remaining_person_days", round(remaining_from_today / board_data.settings.hours_per_day, 2) if board_data.settings.hours_per_day else 0),
        ("if_finished_today.remaining_calendar_days_until_planned_end", (planned_end - today).days if planned_end and planned_end >= today else 0),
        ("if_finished_today.remaining_allocated_value", round(remaining_allocated_value, 2)),
        ("if_finished_today.remaining_delivery_cost", round(remaining_delivery_cost, 2)),
        ("if_finished_today.theoretical_saving", round(remaining_delivery_cost, 2)),
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


def build_activity_economics_dataframe(result: PlanningResult, board_data: BoardData, today: date | None = None) -> pd.DataFrame:
    today = today or date.today()
    rows: list[dict[str, object]] = []
    person_cost_by_id = {person.person_id: (person.daily_cost if person.daily_cost and person.daily_cost > 0 else 0) for person in board_data.people}
    for activity in board_data.activities:
        if activity.status != STATUS_PLANNED:
            continue
        daily_price = activity.daily_price if activity.daily_price and activity.daily_price > 0 else 0
        activity_allocations = [a for a in result.allocations if a.activity_id == activity.activity_id]
        allocated_hours = sum(a.hours for a in activity_allocations)
        delivered_hours = sum(a.hours for a in activity_allocations if a.date <= today)
        remaining_hours = sum(a.hours for a in activity_allocations if a.date > today)
        delivered_cost = sum((a.hours / 8) * person_cost_by_id.get(a.person_id, 0) for a in activity_allocations if a.date <= today)
        estimated_delivery_cost = sum((a.hours / 8) * person_cost_by_id.get(a.person_id, 0) for a in activity_allocations)
        remaining_delivery_cost = sum((a.hours / 8) * person_cost_by_id.get(a.person_id, 0) for a in activity_allocations if a.date > today)
        estimated_person_days = activity.estimated_hours / 8 if activity.estimated_hours else 0
        allocated_person_days = allocated_hours / 8 if allocated_hours else 0
        allocated_value = allocated_person_days * daily_price
        delivered_value = (delivered_hours / 8) * daily_price
        remaining_value = (remaining_hours / 8) * daily_price
        expected_margin = (estimated_person_days * daily_price) - estimated_delivery_cost
        expected_margin_percentage = (expected_margin / (estimated_person_days * daily_price) * 100) if estimated_person_days and daily_price else 0
        rows.append(
            {
                "activity_id": activity.activity_id,
                "activity_name": activity.name,
                "status": activity.status,
                "estimated_hours": round(activity.estimated_hours, 2),
                "estimated_person_days": round(estimated_person_days, 2),
                "daily_price": round(daily_price, 2),
                "estimated_value": round(estimated_person_days * daily_price, 2),
                "allocated_hours": round(allocated_hours, 2),
                "allocated_person_days": round(allocated_person_days, 2),
                "allocated_value": round(allocated_value, 2),
                "remaining_allocated_hours_from_today": round(remaining_hours, 2),
                "remaining_allocated_value_from_today": round(remaining_value, 2),
                "delivered_hours_until_today": round(delivered_hours, 2),
                "delivered_value_until_today": round(delivered_value, 2),
                "delivered_cost_until_today": round(delivered_cost, 2),
                "estimated_delivery_cost": round(estimated_delivery_cost, 2),
                "remaining_delivery_cost_from_today": round(remaining_delivery_cost, 2),
                "expected_margin": round(expected_margin, 2),
                "expected_margin_percentage": round(expected_margin_percentage, 2),
                "theoretical_saving_if_finished_today": round(remaining_delivery_cost, 2),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "activity_id",
            "activity_name",
            "status",
            "estimated_hours",
            "estimated_person_days",
            "daily_price",
            "estimated_value",
            "allocated_hours",
            "allocated_person_days",
            "allocated_value",
            "remaining_allocated_hours_from_today",
            "remaining_allocated_value_from_today",
            "delivered_hours_until_today",
            "delivered_value_until_today",
            "delivered_cost_until_today",
            "estimated_delivery_cost",
            "remaining_delivery_cost_from_today",
            "expected_margin",
            "expected_margin_percentage",
            "theoretical_saving_if_finished_today",
        ],
    )


def build_person_economics_dataframe(result: PlanningResult, board_data: BoardData, today: date | None = None) -> pd.DataFrame:
    today = today or date.today()
    rows: list[dict[str, object]] = []
    for person in sorted([p for p in board_data.people if p.active], key=lambda p: p.person_id):
        daily_cost = person.daily_cost if person.daily_cost and person.daily_cost > 0 else 0
        allocations = [a for a in result.allocations if a.person_id == person.person_id]
        total_hours = sum(a.hours for a in allocations)
        delivered_hours = sum(a.hours for a in allocations if a.date <= today)
        remaining_hours = sum(a.hours for a in allocations if a.date > today)
        allocated_until = max((a.date for a in allocations), default=None)
        rows.append(
            {
                "person_id": person.person_id,
                "person_name": person.name,
                "daily_cost": round(daily_cost, 2),
                "allocated_hours_total": round(total_hours, 2),
                "allocated_person_days_total": round(total_hours / 8, 2),
                "estimated_delivery_cost": round((total_hours / 8) * daily_cost, 2),
                "delivered_hours_until_today": round(delivered_hours, 2),
                "delivered_cost_until_today": round((delivered_hours / 8) * daily_cost, 2),
                "remaining_hours_from_today": round(remaining_hours, 2),
                "remaining_delivery_cost_from_today": round((remaining_hours / 8) * daily_cost, 2),
                "allocated_until": allocated_until.isoformat() if allocated_until else "",
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "person_id",
            "person_name",
            "daily_cost",
            "allocated_hours_total",
            "allocated_person_days_total",
            "estimated_delivery_cost",
            "delivered_hours_until_today",
            "delivered_cost_until_today",
            "remaining_hours_from_today",
            "remaining_delivery_cost_from_today",
            "allocated_until",
        ],
    )
