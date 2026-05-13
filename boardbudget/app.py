from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from boardbudget.config import APP_NAME, BOARDS_DIR
from boardbudget.dashboard import build_calendar_dataframe, build_dashboard_dataframe, build_warnings_dataframe
from boardbudget.excel_store import create_new_board_file, duplicate_board, list_board_files, load_board, save_board, write_generated_sheets
from boardbudget.planner_engine import calculate_plan
from boardbudget.sample_data import create_sample_board
from boardbudget.ui.pages import (
    render_activities_editor,
    render_assignments_editor,
    render_calendar,
    render_dashboard,
    render_people_editor,
    render_raw_excel_info,
    render_warnings,
)


def _safe_filename(name: str) -> str:
    keep = [c if c.isalnum() or c in ("-", "_") else "_" for c in name.strip()]
    cleaned = "".join(keep).strip("_")
    return cleaned or "board"


def _recalculate_board(path: Path) -> None:
    board_data = load_board(path)
    result = calculate_plan(board_data)
    calendar_df = build_calendar_dataframe(result, board_data)
    dashboard_df = build_dashboard_dataframe(result, board_data)
    warnings_df = build_warnings_dataframe(result.warnings)
    write_generated_sheets(path, calendar_df, dashboard_df, warnings_df)


def _create_sidebar() -> Path | None:
    BOARDS_DIR.mkdir(parents=True, exist_ok=True)
    st.sidebar.caption(f"Boards folder: `{BOARDS_DIR}`")

    boards = list_board_files(BOARDS_DIR)
    if boards:
        selected_name = st.sidebar.selectbox("Open board", [p.name for p in boards])
        selected = BOARDS_DIR / selected_name
    else:
        st.sidebar.info("No boards yet.")
        selected = None

    with st.sidebar.expander("Create new board"):
        new_name = st.text_input("Board name", value="New Board")
        new_start = st.date_input("Start date", value=date.today())
        if st.button("Create board", use_container_width=True):
            path = BOARDS_DIR / f"{_safe_filename(new_name)}.xlsx"
            create_new_board_file(path, new_name, new_start)
            st.success(f"Created {path.name}")
            st.rerun()

    if selected:
        duplicate_name = st.sidebar.text_input("Duplicate as", value=f"{selected.stem}_copy.xlsx")
        if st.sidebar.button("Duplicate selected board", use_container_width=True):
            target = BOARDS_DIR / duplicate_name
            if target.suffix.lower() != ".xlsx":
                target = target.with_suffix(".xlsx")
            duplicate_board(selected, target)
            st.sidebar.success(f"Duplicated to {target.name}")
            st.rerun()

        if st.sidebar.button("Recalculate current board", type="primary", use_container_width=True):
            _recalculate_board(selected)
            st.sidebar.success("Recalculated generated sheets.")
            st.rerun()

        with selected.open("rb") as file:
            st.sidebar.download_button(
                "Download current board",
                data=file,
                file_name=selected.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    if st.sidebar.button("Create sample board", use_container_width=True):
        sample_path = BOARDS_DIR / "pitagora_sample.xlsx"
        create_sample_board(sample_path)
        _recalculate_board(sample_path)
        st.sidebar.success("Created sample board.")
        st.rerun()

    return selected


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)

    selected = _create_sidebar()
    if selected is None:
        st.info("Create a board or sample board from the sidebar.")
        return

    board_data = load_board(selected)
    result = calculate_plan(board_data)
    calendar_df = build_calendar_dataframe(result, board_data)
    dashboard_df = build_dashboard_dataframe(result, board_data)
    warnings_df = build_warnings_dataframe(result.warnings)

    tabs = st.tabs(["Dashboard", "People", "Activities", "Assignments", "Calendar", "Warnings", "Raw Excel Info"])

    with tabs[0]:
        render_dashboard(board_data, dashboard_df, result)

    with tabs[1]:
        people = render_people_editor(board_data)
        if people is not None:
            board_data.people = people
            save_board(selected, board_data)
            st.success("People saved.")
            st.rerun()

    with tabs[2]:
        activities = render_activities_editor(board_data)
        if activities is not None:
            board_data.activities = activities
            save_board(selected, board_data)
            st.success("Activities saved.")
            st.rerun()

    with tabs[3]:
        assignments = render_assignments_editor(board_data)
        if assignments is not None:
            board_data.assignments = assignments
            save_board(selected, board_data)
            st.success("Assignments saved.")
            st.rerun()

    with tabs[4]:
        render_calendar(calendar_df)

    with tabs[5]:
        render_warnings(warnings_df)

    with tabs[6]:
        render_raw_excel_info(selected)


if __name__ == "__main__":
    main()
