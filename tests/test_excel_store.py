from __future__ import annotations

from datetime import date

import pandas as pd
from openpyxl import load_workbook

from boardbudget.excel_store import create_new_board_file, load_board, save_board, write_generated_sheets
from boardbudget.models import Activity, Assignment, BoardData, BoardSettings, Person


def test_create_and_load_board_file(tmp_path) -> None:
    path = tmp_path / "board.xlsx"

    create_new_board_file(path, "My Board", date(2026, 5, 13))
    loaded = load_board(path)

    assert loaded.settings.board_name == "My Board"
    assert loaded.settings.start_date == date(2026, 5, 13)
    assert [p.person_id for p in loaded.people] == ["P1", "P2"]


def test_save_board_and_write_generated_sheets(tmp_path) -> None:
    path = tmp_path / "board.xlsx"
    board = BoardData(
        settings=BoardSettings("Excel", date(2026, 5, 13)),
        people=[Person("P1", "One", 8, True)],
        activities=[Activity("A1", 1, "Work", 8, 8, "PLANNED")],
        assignments=[Assignment("A1", "P1")],
    )

    save_board(path, board)
    write_generated_sheets(
        path,
        pd.DataFrame([{"date": "2026-05-13", "person_id": "P1", "person_name": "One", "activity_id": "A1", "activity_name": "Work", "hours": 8}]),
        pd.DataFrame([{"metric": "total_allocated_hours", "value": 8}]),
        pd.DataFrame([{"level": "INFO", "code": "OK", "message": "ok"}]),
    )

    workbook = load_workbook(path, read_only=True)
    assert {"01_Board", "02_People", "03_Activities", "04_Assignments", "05_Calendar", "06_Dashboard", "07_Warnings"}.issubset(
        set(workbook.sheetnames)
    )
    loaded = load_board(path)
    assert loaded.activities[0].activity_id == "A1"

