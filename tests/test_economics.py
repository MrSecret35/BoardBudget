from __future__ import annotations

from datetime import date

import pandas as pd

from boardbudget.dashboard import build_activity_economics_dataframe, build_dashboard_dataframe, build_person_economics_dataframe
from boardbudget.models import Activity, Assignment, BoardData, BoardSettings, CalendarAllocation, Person
from boardbudget.planner_engine import PlanningResult, calculate_plan
from boardbudget.ui.aggrid import build_grid_options


def test_missing_daily_cost_defaults_to_zero_and_warns() -> None:
    board = BoardData(
        BoardSettings("Costs", date(2026, 5, 13)),
        [Person("P1", "One", 8, True)],
        [Activity("A1", 1, "Work", 8, 8, "PLANNED", "", daily_price=400)],
        [Assignment("A1", "P1")],
    )

    result = calculate_plan(board)

    assert any(w.code == "MISSING_DAILY_COST" for w in result.warnings)


def test_delivered_cost_until_today() -> None:
    board = BoardData(BoardSettings("Costs", date(2026, 5, 13)), [Person("P1", "One", 8, True, 400)])
    result = PlanningResult(
        allocations=[
            CalendarAllocation(date(2026, 5, 13), "P1", "One", "A1", "Work", 8),
            CalendarAllocation(date(2026, 5, 14), "P1", "One", "A1", "Work", 4),
            CalendarAllocation(date(2026, 5, 15), "P1", "One", "A1", "Work", 8),
        ]
    )

    people = build_person_economics_dataframe(result, board, today=date(2026, 5, 14))

    assert people.loc[0, "delivered_cost_until_today"] == 600


def test_estimated_delivery_cost_uses_person_costs() -> None:
    board = BoardData(BoardSettings("Costs", date(2026, 5, 13)), [Person("P1", "One", 8, True, 400), Person("P2", "Two", 8, True, 300)])
    result = PlanningResult(
        allocations=[
            CalendarAllocation(date(2026, 5, 13), "P1", "One", "A1", "Work", 8),
            CalendarAllocation(date(2026, 5, 13), "P2", "Two", "A1", "Work", 4),
        ]
    )

    people = build_person_economics_dataframe(result, board, today=date(2026, 5, 13))

    assert people["estimated_delivery_cost"].sum() == 550


def test_expected_margin_dashboard_metric() -> None:
    board = BoardData(
        BoardSettings("Costs", date(2026, 5, 13)),
        [Person("P1", "One", 8, True, 300)],
        [Activity("A1", 1, "Work", 16, 8, "PLANNED", "", daily_price=500)],
        [Assignment("A1", "P1")],
    )
    result = PlanningResult(
        allocations=[
            CalendarAllocation(date(2026, 5, 13), "P1", "One", "A1", "Work", 8),
            CalendarAllocation(date(2026, 5, 14), "P1", "One", "A1", "Work", 8),
        ]
    )

    metrics = dict(zip(build_dashboard_dataframe(result, board, today=date(2026, 5, 13))["metric"], build_dashboard_dataframe(result, board, today=date(2026, 5, 13))["value"]))

    assert metrics["total_estimated_value"] == 1000
    assert metrics["estimated_delivery_cost"] == 600
    assert metrics["expected_margin"] == 400


def test_activity_economics_uses_person_cost_for_margin() -> None:
    board = BoardData(
        BoardSettings("Costs", date(2026, 5, 13)),
        [Person("P1", "One", 8, True, 300)],
        [Activity("A1", 1, "Work", 8, 8, "PLANNED", "", daily_price=500)],
        [Assignment("A1", "P1")],
    )
    result = PlanningResult(allocations=[CalendarAllocation(date(2026, 5, 13), "P1", "One", "A1", "Work", 8)])

    economics = build_activity_economics_dataframe(result, board, today=date(2026, 5, 13))

    assert economics.loc[0, "allocated_value"] == 500
    assert economics.loc[0, "estimated_delivery_cost"] == 300
    assert economics.loc[0, "expected_margin"] == 200


def test_person_economics_summary() -> None:
    board = BoardData(BoardSettings("Costs", date(2026, 5, 13)), [Person("P1", "One", 8, True, 400)])
    result = PlanningResult(
        allocations=[
            CalendarAllocation(date(2026, 5, 13), "P1", "One", "A1", "Work", 8),
            CalendarAllocation(date(2026, 5, 15), "P1", "One", "A1", "Work", 4),
        ]
    )

    people = build_person_economics_dataframe(result, board, today=date(2026, 5, 13))

    assert people.loc[0, "allocated_hours_total"] == 12
    assert people.loc[0, "estimated_delivery_cost"] == 600
    assert people.loc[0, "remaining_delivery_cost_from_today"] == 200


def test_grid_options_are_sortable_and_resizable() -> None:
    options = build_grid_options(pd.DataFrame([{"metric": "x", "value": 1}]), column_widths={"metric": 320})

    assert options["defaultColDef"]["sortable"] is True
    assert options["defaultColDef"]["resizable"] is True
    assert options["defaultColDef"]["sortingOrder"] == ["asc", "desc", None]
