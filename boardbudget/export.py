from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .dashboard import (
    build_activity_economics_dataframe,
    build_calendar_dataframe,
    build_dashboard_dataframe,
    build_person_economics_dataframe,
    build_warnings_dataframe,
)
from .excel_store import load_board, write_generated_sheets
from .planner_engine import calculate_plan


def recalculate_board_file(path: Path) -> None:
    board_data = load_board(path)
    result = calculate_plan(board_data)
    calendar_df = build_calendar_dataframe(result, board_data)
    economics_df = build_activity_economics_dataframe(result, board_data)
    person_economics_df = build_person_economics_dataframe(result, board_data)
    dashboard_df = build_dashboard_dataframe(result, board_data)
    warnings_df = build_warnings_dataframe(result.warnings)
    write_generated_sheets(path, calendar_df, dashboard_df, warnings_df, economics_df, person_economics_df)


def prepare_board_download_file(board_path: Path) -> bytes:
    with tempfile.TemporaryDirectory(prefix="boardbudget_export_") as tmp_dir:
        export_path = Path(tmp_dir) / board_path.name
        shutil.copy2(board_path, export_path)
        recalculate_board_file(export_path)
        return export_path.read_bytes()
