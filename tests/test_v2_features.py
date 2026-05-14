from __future__ import annotations

from datetime import date

import pytest

from boardbudget.assignment_utils import assignments_from_activity_people, planned_activity_options
from boardbudget.calendar_utils import classify_day, get_italian_holidays_for_years
from boardbudget.dashboard import build_activity_economics_dataframe, build_calendar_dataframe, build_calendar_pivot_dataframe
from boardbudget.estimates import EstimateExpressionError, normalize_estimates, parse_number_expression
from boardbudget.models import Activity, Assignment, BoardData, BoardSettings, Person
from boardbudget.planner_engine import calculate_plan
from boardbudget.ui.aggrid import render_calendar_grid


def board(
    *,
    start_date: date = date(2026, 5, 15),
    people: list[Person] | None = None,
    activities: list[Activity] | None = None,
    assignments: list[Assignment] | None = None,
) -> BoardData:
    return BoardData(
        settings=BoardSettings("V2", start_date, 8),
        people=people or [Person("P1", "Person 1", 8, True)],
        activities=activities or [],
        assignments=assignments or [],
    )


def test_calendar_pivot_includes_weekends_between_friday_and_monday() -> None:
    data = board(
        activities=[Activity("A1", 1, "Work", 16, 8, "PLANNED", "", daily_price=400)],
        assignments=[Assignment("A1", "P1")],
    )
    result = calculate_plan(data)
    calendar_df = build_calendar_dataframe(result, data)
    pivot = build_calendar_pivot_dataframe(calendar_df, data)

    assert pivot["date"].tolist() == ["2026-05-15", "2026-05-16", "2026-05-17", "2026-05-18"]
    weekend_rows = pivot[pivot["day_type"] == "WEEKEND"]
    assert weekend_rows["P1"].tolist() == ["", ""]


def test_italian_weekday_holiday_is_skipped_and_visible_in_pivot() -> None:
    data = board(
        start_date=date(2026, 6, 1),
        activities=[Activity("A1", 1, "Work", 16, 8, "PLANNED", "", daily_price=400)],
        assignments=[Assignment("A1", "P1")],
    )
    result = calculate_plan(data)
    calendar_df = build_calendar_dataframe(result, data)
    pivot = build_calendar_pivot_dataframe(calendar_df, data)

    assert sorted({a.date for a in result.allocations}) == [date(2026, 6, 1), date(2026, 6, 3)]
    holiday_row = pivot[pivot["date"] == "2026-06-02"].iloc[0]
    assert holiday_row["day_type"] == "HOLIDAY"
    assert holiday_row["holiday_name"]
    assert holiday_row["P1"] == ""


def test_holiday_on_weekday_pushes_work_to_next_working_day() -> None:
    data = board(
        start_date=date(2026, 6, 2),
        activities=[Activity("A1", 1, "Work", 8, 8, "PLANNED", "", daily_price=400)],
        assignments=[Assignment("A1", "P1")],
    )
    result = calculate_plan(data)

    assert [a.date for a in result.allocations] == [date(2026, 6, 3)]


def test_calendar_day_type_classification_for_weekend_and_holiday() -> None:
    holidays_map = get_italian_holidays_for_years({2026})

    assert classify_day(date(2026, 1, 3), holidays_map) == ("WEEKEND", "")
    day_type, holiday_name = classify_day(date(2026, 1, 1), holidays_map)
    assert day_type == "HOLIDAY"
    assert holiday_name


def test_activity_economic_calculation() -> None:
    data = board(
        activities=[Activity("A1", 1, "Analysis", 16, 8, "PLANNED", "", daily_price=400)],
        assignments=[Assignment("A1", "P1")],
    )
    result = calculate_plan(data)
    economics = build_activity_economics_dataframe(result, data, today=date(2026, 5, 15))

    assert economics.loc[0, "estimated_person_days"] == 2
    assert economics.loc[0, "estimated_value"] == 800
    assert economics.loc[0, "allocated_value"] == 800


def test_missing_daily_price_warning() -> None:
    data = board(
        activities=[Activity("A1", 1, "Work", 8, 8, "PLANNED")],
        assignments=[Assignment("A1", "P1")],
    )
    result = calculate_plan(data)

    assert any(w.code == "MISSING_DAILY_PRICE" for w in result.warnings)


def test_shared_activity_with_max_four_hours_per_day_uses_both_people() -> None:
    data = board(
        people=[Person("P1", "One", 8, True), Person("P2", "Two", 8, True)],
        activities=[Activity("A1", 1, "Limited shared", 24, 4, "PLANNED", "", daily_price=400)],
        assignments=[Assignment("A1", "P1"), Assignment("A1", "P2")],
    )
    result = calculate_plan(data)

    day_one = [a for a in result.allocations if a.date == date(2026, 5, 15)]
    assert [(a.person_id, a.hours) for a in day_one] == [("P1", 4), ("P2", 4)]
    assert sum(a.hours for a in result.allocations) == 24


def test_shared_activity_can_be_completed_mainly_by_person_who_reaches_it_first() -> None:
    data = board(
        start_date=date(2026, 5, 13),
        people=[Person("P1", "One", 8, True), Person("P2", "Two", 8, True)],
        activities=[
            Activity("A1", 1, "P1 only", 16, 8, "PLANNED", "", daily_price=400),
            Activity("A2", 2, "Shared", 24, 8, "PLANNED", "", daily_price=400),
        ],
        assignments=[Assignment("A1", "P1"), Assignment("A2", "P1"), Assignment("A2", "P2")],
    )
    result = calculate_plan(data)
    p2_shared = sum(a.hours for a in result.allocations if a.activity_id == "A2" and a.person_id == "P2")
    p1_shared = sum(a.hours for a in result.allocations if a.activity_id == "A2" and a.person_id == "P1")

    assert p2_shared > p1_shared
    assert p2_shared + p1_shared == 24


def test_assignment_matrix_conversion_to_normalized_rows() -> None:
    data = board(
        people=[Person("P1", "One", 8, True), Person("P2", "Two", 8, True)],
        activities=[Activity("A1", 1, "Work", 8, 8, "PLANNED", "", daily_price=400)],
    )

    assignments = assignments_from_activity_people({"A1": ["P1", "P2"]}, data)

    assert assignments == [Assignment("A1", "P1"), Assignment("A1", "P2")]


def test_done_activities_excluded_from_assignment_options() -> None:
    data = board(
        activities=[
            Activity("A1", 1, "Done", 8, 8, "DONE"),
            Activity("A2", 2, "Planned", 8, 8, "PLANNED", "", daily_price=400),
        ]
    )

    assert planned_activity_options(data) == ["A2"]


def test_estimate_expression_parser() -> None:
    assert parse_number_expression("20*8") == 160
    assert parse_number_expression("10/2") == 5
    assert parse_number_expression("2.5*8") == 20
    with pytest.raises(EstimateExpressionError):
        parse_number_expression("__import__('os')")


def test_estimated_days_to_estimated_hours() -> None:
    estimated_days, estimated_hours, warnings = normalize_estimates("A1", "5", "")

    assert estimated_days == 5
    assert estimated_hours == 40
    assert warnings == []


def test_estimated_hours_to_estimated_days() -> None:
    estimated_days, estimated_hours, warnings = normalize_estimates("A1", "", "40")

    assert estimated_days == 5
    assert estimated_hours == 40
    assert warnings == []


def test_estimate_mismatch_warning() -> None:
    estimated_days, estimated_hours, warnings = normalize_estimates("A1", "5", "20")

    assert estimated_days == 2.5
    assert estimated_hours == 20
    assert any(w.code == "ESTIMATE_DAYS_HOURS_MISMATCH" for w in warnings)


def test_blank_and_whitespace_estimates_normalize_without_warning() -> None:
    estimated_days, estimated_hours, warnings = normalize_estimates("A1", "   ", "")

    assert estimated_days is None
    assert estimated_hours == 0
    assert warnings == []


def test_aggrid_helper_import_smoke() -> None:
    assert callable(render_calendar_grid)
