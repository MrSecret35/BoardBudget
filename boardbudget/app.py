from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from boardbudget.config import APP_NAME, BOARDS_DIR
from boardbudget.dashboard import (
    build_activity_economics_dataframe,
    build_calendar_dataframe,
    build_dashboard_dataframe,
    build_person_economics_dataframe,
    build_warnings_dataframe,
)
from boardbudget.excel_store import create_new_board_file, duplicate_board, list_board_files, load_board, save_board
from boardbudget.export import prepare_board_download_file, recalculate_board_file
from boardbudget.planner_engine import calculate_plan
from boardbudget.sample_data import create_sample_board
from boardbudget.settings import DEFAULT_SETTINGS, load_app_settings, save_app_settings
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
    recalculate_board_file(path)


def _init_settings() -> None:
    if "app_settings" not in st.session_state:
        st.session_state["app_settings"] = load_app_settings()


def _apply_app_settings(settings: dict[str, str]) -> None:
    size_map = {"Small": "0.85rem", "Normal": "1rem", "Large": "1.15rem"}
    font_size = size_map.get(settings.get("font_size", "Normal"), "1rem")
    theme = settings.get("theme", "System/default")
    if theme == "Dark":
        background = "#171717"
        text = "#f3f4f6"
        panel = "#222222"
    elif theme == "Light":
        background = "#ffffff"
        text = "#111827"
        panel = "#f8fafc"
    else:
        background = "inherit"
        text = "inherit"
        panel = "inherit"
    st.markdown(
        f"""
        <style>
        html, body, [class*="st-"] {{
            font-size: {font_size};
        }}
        .stApp {{
            background: {background};
            color: {text};
        }}
        section[data-testid="stSidebar"] {{
            background: {panel};
        }}
        [data-testid="stMetricValue"] {{
            font-size: calc({font_size} * 1.55);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_settings() -> dict[str, str]:
    settings = dict(st.session_state.get("app_settings", DEFAULT_SETTINGS))
    def option_index(options: list[str], value: str) -> int:
        return options.index(value) if value in options else 0

    st.sidebar.divider()
    with st.sidebar.expander("⚙️ Settings", expanded=False):
        font_options = ["Small", "Normal", "Large"]
        settings["font_size"] = st.selectbox(
            "Font size scale",
            font_options,
            index=option_index(font_options, settings.get("font_size", "Normal")),
        )
        theme_options = ["System/default", "Light", "Dark"]
        settings["theme"] = st.selectbox(
            "Theme preference",
            theme_options,
            index=option_index(theme_options, settings.get("theme", "System/default")),
        )
        settings["non_working_day_color"] = st.color_picker(
            "Non-working day color",
            settings.get("non_working_day_color", DEFAULT_SETTINGS["non_working_day_color"]),
        )
        st.caption("Full Streamlit theme switching may require config.toml and app restart.")
        if st.button("Save settings", use_container_width=True):
            try:
                save_app_settings(settings)
                st.session_state["app_settings"] = settings
                st.success("Settings saved.")
            except OSError as exc:
                st.error(f"Could not save settings: {exc}")
    st.session_state["app_settings"] = settings
    return settings


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
            try:
                path = BOARDS_DIR / f"{_safe_filename(new_name)}.xlsx"
                create_new_board_file(path, new_name, new_start)
                st.success(f"Created {path.name}")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not create board: {exc}")

    if selected:
        duplicate_name = st.sidebar.text_input("Duplicate as", value=f"{selected.stem}_copy.xlsx")
        if st.sidebar.button("Duplicate selected board", use_container_width=True):
            try:
                target = BOARDS_DIR / duplicate_name
                if target.suffix.lower() != ".xlsx":
                    target = target.with_suffix(".xlsx")
                duplicate_board(selected, target)
                st.sidebar.success(f"Duplicated to {target.name}")
                st.rerun()
            except Exception as exc:
                st.sidebar.error(f"Could not duplicate board: {exc}")

        if st.sidebar.button("Recalculate current board", type="primary", use_container_width=True):
            try:
                _recalculate_board(selected)
                st.sidebar.success("Recalculated generated sheets.")
                st.rerun()
            except Exception as exc:
                st.sidebar.error(f"Could not recalculate board: {exc}")

        try:
            download_bytes = prepare_board_download_file(selected)
            st.sidebar.download_button(
                "Download current board",
                data=download_bytes,
                file_name=selected.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as exc:
            st.sidebar.error(f"Could not prepare Excel download: {exc}")

    if st.sidebar.button("Create sample board", use_container_width=True):
        try:
            sample_path = BOARDS_DIR / "pitagora_sample.xlsx"
            create_sample_board(sample_path)
            _recalculate_board(sample_path)
            st.sidebar.success("Created sample board.")
            st.rerun()
        except Exception as exc:
            st.sidebar.error(f"Could not create sample board: {exc}")

    _render_sidebar_settings()

    return selected


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    _init_settings()
    _apply_app_settings(st.session_state["app_settings"])
    st.title(APP_NAME)

    selected = _create_sidebar()
    if selected is None:
        st.info("Create a board or sample board from the sidebar.")
        return

    board_data = load_board(selected)
    result = calculate_plan(board_data)
    calendar_df = build_calendar_dataframe(result, board_data)
    economics_df = build_activity_economics_dataframe(result, board_data)
    person_economics_df = build_person_economics_dataframe(result, board_data)
    dashboard_df = build_dashboard_dataframe(result, board_data)
    warnings_df = build_warnings_dataframe(result.warnings)

    tabs = st.tabs(["Dashboard", "People", "Activities", "Assignments", "Calendar", "Warnings", "Raw Excel Info"])

    with tabs[0]:
        render_dashboard(board_data, dashboard_df, economics_df, person_economics_df, result)

    with tabs[1]:
        people = render_people_editor(board_data)
        if people is not None:
            try:
                board_data.people = people
                save_board(selected, board_data)
                st.success("People saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save people: {exc}")

    with tabs[2]:
        activities = render_activities_editor(board_data)
        if activities is not None:
            try:
                board_data.activities = activities
                save_board(selected, board_data)
                st.success("Activities saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save activities: {exc}")

    with tabs[3]:
        assignments = render_assignments_editor(board_data)
        if assignments is not None:
            try:
                board_data.assignments = assignments
                save_board(selected, board_data)
                st.success("Assignments saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save assignments: {exc}")

    with tabs[4]:
        settings = st.session_state.get("app_settings", DEFAULT_SETTINGS)
        render_calendar(calendar_df, board_data, settings.get("non_working_day_color", DEFAULT_SETTINGS["non_working_day_color"]))

    with tabs[5]:
        render_warnings(warnings_df)

    with tabs[6]:
        render_raw_excel_info(selected)


if __name__ == "__main__":
    main()
