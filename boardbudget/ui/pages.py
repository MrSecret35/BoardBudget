from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from boardbudget.config import ACTIVITIES_SHEET, ASSIGNMENTS_SHEET, BOARD_SHEET, PEOPLE_SHEET
from boardbudget.dashboard import (
    build_activity_summary_dataframe,
    build_calendar_pivot_dataframe,
    build_person_summary_dataframe,
)
from boardbudget.excel_store import get_sheet_names
from boardbudget.models import Activity, Assignment, BoardData, Person
from boardbudget.ui.components import show_dataframe_or_empty, status_column_config


def render_dashboard(board_data: BoardData, dashboard_df: pd.DataFrame, result) -> None:
    cols = st.columns(4)
    values = dict(zip(dashboard_df.get("metric", []), dashboard_df.get("value", [])))
    cols[0].metric("Allocated hours", values.get("total_allocated_hours", 0))
    cols[1].metric("Working days", values.get("total_working_days", 0))
    cols[2].metric("Plan end", values.get("planned_end_date", ""))
    cols[3].metric("Remaining hours", values.get("remaining_hours_from_today", 0))
    show_dataframe_or_empty(dashboard_df, "No dashboard metrics yet.")
    st.subheader("People")
    show_dataframe_or_empty(build_person_summary_dataframe(result, board_data), "No people allocation yet.")
    st.subheader("Activities")
    show_dataframe_or_empty(build_activity_summary_dataframe(result, board_data), "No activity allocation yet.")


def render_people_editor(board_data: BoardData) -> list[Person] | None:
    df = pd.DataFrame([p.__dict__ for p in board_data.people], columns=["person_id", "name", "hours_per_day", "active"])
    edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", hide_index=True)
    if st.button("Save people", type="primary"):
        return [
            Person(
                person_id=str(row.get("person_id", "")).strip(),
                name=str(row.get("name", "")).strip(),
                hours_per_day=row.get("hours_per_day") if pd.notna(row.get("hours_per_day")) else None,
                active=bool(row.get("active", True)),
            )
            for _, row in edited.iterrows()
            if any(pd.notna(row.get(column)) and str(row.get(column)).strip() != "" for column in edited.columns)
        ]
    return None


def render_activities_editor(board_data: BoardData) -> list[Activity] | None:
    df = pd.DataFrame([a.__dict__ for a in board_data.activities], columns=["activity_id", "order", "name", "estimated_hours", "max_hours_per_day", "status", "notes"])
    edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", hide_index=True, column_config=status_column_config())
    if st.button("Save activities", type="primary"):
        rows: list[Activity] = []
        for _, row in edited.iterrows():
            if not any(pd.notna(row.get(column)) and str(row.get(column)).strip() != "" for column in edited.columns):
                continue
            order = row.get("order")
            rows.append(
                Activity(
                    activity_id=str(row.get("activity_id", "")).strip(),
                    order=int(order) if pd.notna(order) and str(order).strip() != "" else None,
                    name=str(row.get("name", "")).strip(),
                    estimated_hours=float(row.get("estimated_hours") or 0),
                    max_hours_per_day=float(row.get("max_hours_per_day")) if pd.notna(row.get("max_hours_per_day")) and str(row.get("max_hours_per_day")).strip() != "" else None,
                    status=str(row.get("status") or "PLANNED").strip().upper(),
                    notes=str(row.get("notes") or "").strip(),
                )
            )
        return rows
    return None


def render_assignments_editor(board_data: BoardData) -> list[Assignment] | None:
    df = pd.DataFrame([a.__dict__ for a in board_data.assignments], columns=["activity_id", "person_id"])
    edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", hide_index=True)
    if st.button("Save assignments", type="primary"):
        return [
            Assignment(activity_id=str(row.get("activity_id", "")).strip(), person_id=str(row.get("person_id", "")).strip())
            for _, row in edited.iterrows()
            if any(pd.notna(row.get(column)) and str(row.get(column)).strip() != "" for column in edited.columns)
        ]
    return None


def render_calendar(calendar_df: pd.DataFrame) -> None:
    st.subheader("Pivot calendar")
    show_dataframe_or_empty(build_calendar_pivot_dataframe(calendar_df), "No calendar allocations yet.")
    st.subheader("Raw allocations")
    show_dataframe_or_empty(calendar_df, "No raw allocation rows yet.")


def render_warnings(warnings_df: pd.DataFrame) -> None:
    if not warnings_df.empty and (warnings_df["level"] == "ERROR").any():
        st.error("This board has validation or planning errors.")
    elif not warnings_df.empty and (warnings_df["level"] == "WARNING").any():
        st.warning("This board has warnings.")
    show_dataframe_or_empty(warnings_df, "No warnings.")


def render_raw_excel_info(path: Path) -> None:
    st.write(f"Board file: `{path}`")
    st.write("Sheets:")
    for sheet in get_sheet_names(path):
        st.write(f"- {sheet}")
    st.info(
        f"`05_Calendar`, `06_Dashboard`, and `07_Warnings` are generated by the app. "
        f"Edit `{BOARD_SHEET}`, `{PEOPLE_SHEET}`, `{ACTIVITIES_SHEET}`, and `{ASSIGNMENTS_SHEET}` directly only if you want to work in Excel."
    )

