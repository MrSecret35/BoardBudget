from __future__ import annotations

from datetime import date

from boardbudget.models import Activity, Assignment, BoardData, BoardSettings, Person
from boardbudget.planner_engine import calculate_plan


def board(
    *,
    start_date: date = date(2026, 5, 13),
    people: list[Person] | None = None,
    activities: list[Activity] | None = None,
    assignments: list[Assignment] | None = None,
) -> BoardData:
    return BoardData(
        settings=BoardSettings("Test Board", start_date, 8),
        people=people or [Person("P1", "Person 1", 8, True)],
        activities=activities or [],
        assignments=assignments or [],
    )


def hours_by_person(result, activity_id: str) -> dict[str, float]:
    totals: dict[str, float] = {}
    for allocation in result.allocations:
        if allocation.activity_id == activity_id:
            totals[allocation.person_id] = totals.get(allocation.person_id, 0) + allocation.hours
    return totals


def test_single_person_single_activity_two_working_days() -> None:
    result = calculate_plan(
        board(
            activities=[Activity("A1", 1, "Analysis", 16, 8, "PLANNED")],
            assignments=[Assignment("A1", "P1")],
        )
    )

    assert sum(a.hours for a in result.allocations) == 16
    assert sorted({a.date for a in result.allocations}) == [date(2026, 5, 13), date(2026, 5, 14)]


def test_shared_activity_split_equally() -> None:
    result = calculate_plan(
        board(
            people=[Person("P1", "Person 1", 8, True), Person("P2", "Person 2", 8, True)],
            activities=[Activity("A1", 1, "Shared", 40, 8, "PLANNED")],
            assignments=[Assignment("A1", "P1"), Assignment("A1", "P2")],
        )
    )

    assert hours_by_person(result, "A1") == {"P1": 20, "P2": 20}


def test_shared_independent_planning() -> None:
    result = calculate_plan(
        board(
            people=[Person("P1", "Person 1", 8, True), Person("P2", "Person 2", 8, True)],
            activities=[
                Activity("A1", 1, "First", 16, 8, "PLANNED"),
                Activity("A2", 2, "Shared", 40, 8, "PLANNED"),
            ],
            assignments=[Assignment("A1", "P1"), Assignment("A2", "P1"), Assignment("A2", "P2")],
        )
    )

    p2_a2_dates = [a.date for a in result.allocations if a.person_id == "P2" and a.activity_id == "A2"]
    p1_a2_dates = [a.date for a in result.allocations if a.person_id == "P1" and a.activity_id == "A2"]
    assert min(p2_a2_dates) == date(2026, 5, 13)
    assert min(p1_a2_dates) == date(2026, 5, 15)


def test_max_four_hours_per_day_fills_remaining_capacity() -> None:
    result = calculate_plan(
        board(
            activities=[
                Activity("A1", 1, "Limited", 8, 4, "PLANNED"),
                Activity("A2", 2, "Next", 8, 8, "PLANNED"),
            ],
            assignments=[Assignment("A1", "P1"), Assignment("A2", "P1")],
        )
    )

    day_one = [a for a in result.allocations if a.date == date(2026, 5, 13)]
    assert [(a.activity_id, a.hours) for a in day_one] == [("A1", 4), ("A2", 4)]


def test_monday_to_friday_only() -> None:
    result = calculate_plan(
        board(
            start_date=date(2026, 5, 15),
            activities=[Activity("A1", 1, "Work", 16, 8, "PLANNED")],
            assignments=[Assignment("A1", "P1")],
        )
    )

    assert sorted({a.date for a in result.allocations}) == [date(2026, 5, 15), date(2026, 5, 18)]


def test_done_activity_skipped() -> None:
    result = calculate_plan(
        board(
            activities=[Activity("A1", 1, "Done", 16, 8, "DONE")],
            assignments=[Assignment("A1", "P1")],
        )
    )

    assert result.allocations == []


def test_activity_without_assignment_warning() -> None:
    result = calculate_plan(board(activities=[Activity("A1", 1, "Unassigned", 8, 8, "PLANNED")]))

    assert any(w.code == "ACTIVITY_WITHOUT_ASSIGNMENT" for w in result.warnings)


def test_duplicate_assignments_ignored() -> None:
    result = calculate_plan(
        board(
            activities=[Activity("A1", 1, "Work", 8, 8, "PLANNED")],
            assignments=[Assignment("A1", "P1"), Assignment("A1", "P1")],
        )
    )

    assert sum(a.hours for a in result.allocations) == 8
    assert any(w.code == "DUPLICATE_ASSIGNMENT" for w in result.warnings)


def test_invalid_max_hours_per_day_defaults_to_eight() -> None:
    result = calculate_plan(
        board(
            activities=[Activity("A1", 1, "Work", 8, 0, "PLANNED")],
            assignments=[Assignment("A1", "P1")],
        )
    )

    assert len(result.allocations) == 1
    assert result.allocations[0].hours == 8


def test_deterministic_ordering_uses_activity_id_tiebreaker() -> None:
    result = calculate_plan(
        board(
            activities=[
                Activity("A2", 1, "Second Id", 8, 8, "PLANNED"),
                Activity("A1", 1, "First Id", 8, 8, "PLANNED"),
            ],
            assignments=[Assignment("A1", "P1"), Assignment("A2", "P1")],
        )
    )

    assert [a.activity_id for a in result.allocations] == ["A1", "A2"]

