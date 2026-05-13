from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from .excel_store import save_board
from .models import Activity, Assignment, BoardData, BoardSettings, Person


def _next_weekday_from_today(today: date) -> date:
    if today.weekday() < 5:
        return today
    return today + timedelta(days=7 - today.weekday())


def create_sample_board(path: Path) -> None:
    start_date = _next_weekday_from_today(date.today())
    board = BoardData(
        settings=BoardSettings(board_name="Pitagora Sample", start_date=start_date),
        people=[
            Person("P1", "Giorgio", 8, True),
            Person("P2", "Colleague", 8, True),
        ],
        activities=[
            Activity("A1", 1, "Analysis", 16, 8, "PLANNED", ""),
            Activity("A2", 2, "Shared development", 40, 8, "PLANNED", ""),
            Activity("A3", 3, "Support and testing", 24, 4, "PLANNED", ""),
            Activity("A4", 4, "Final check", 8, 8, "PLANNED", ""),
        ],
        assignments=[
            Assignment("A1", "P1"),
            Assignment("A2", "P1"),
            Assignment("A2", "P2"),
            Assignment("A3", "P1"),
            Assignment("A3", "P2"),
            Assignment("A4", "P2"),
        ],
    )
    save_board(path, board)

