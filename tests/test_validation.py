from __future__ import annotations

from datetime import date

from boardbudget.models import Activity, Assignment, BoardData, BoardSettings, Person
from boardbudget.validation import validate_board_data


def test_validation_reports_duplicate_ids_and_invalid_assignment() -> None:
    board = BoardData(
        settings=BoardSettings("Validation", date(2026, 5, 13)),
        people=[Person("P1", "One", 8, True), Person("P1", "Duplicate", 8, True)],
        activities=[Activity("A1", 1, "Work", 8, 8, "PLANNED"), Activity("A1", 2, "Again", 8, 8, "PLANNED")],
        assignments=[Assignment("A9", "P9")],
    )

    codes = {warning.code for warning in validate_board_data(board)}

    assert "DUPLICATE_PERSON_ID" in codes
    assert "DUPLICATE_ACTIVITY_ID" in codes
    assert "ASSIGNMENT_UNKNOWN_ACTIVITY" in codes
    assert "ASSIGNMENT_UNKNOWN_PERSON" in codes


def test_validation_reports_invalid_activity_inputs() -> None:
    board = BoardData(
        settings=BoardSettings("Validation", date(2026, 5, 13)),
        people=[Person("P1", "One", 8, True)],
        activities=[Activity("A1", None, "Work", 0, 0, "UNKNOWN")],
        assignments=[Assignment("A1", "P1")],
    )

    codes = {warning.code for warning in validate_board_data(board)}

    assert "INVALID_ESTIMATED_HOURS" in codes
    assert "MISSING_ORDER" in codes
    assert "INVALID_STATUS" in codes
    assert "INVALID_MAX_HOURS" in codes

