from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from boardbudget.assignment_utils import (
    active_person_options,
    assignments_from_activity_people,
    person_label_map,
    planned_activity_options,
)
from boardbudget.config import ACTIVITIES_SHEET, ASSIGNMENTS_SHEET, BOARD_SHEET, PEOPLE_SHEET
from boardbudget.dashboard import (
    build_activity_summary_dataframe,
    build_calendar_pivot_dataframe,
    build_person_summary_dataframe,
)
from boardbudget.estimates import normalize_estimates
from boardbudget.excel_store import get_sheet_names
from boardbudget.models import Activity, Assignment, BoardData, Person
from boardbudget.ui.components import (
    activity_column_config,
    calendar_column_config,
    people_column_config,
    raw_assignment_column_config,
    show_dataframe_or_empty,
)


def _eur(value: object) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    return f"€ {amount:,.2f}"


def format_editable_number(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text == "":
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return f"{number:g}"


def _optional_float(value: object, field_name: str) -> float | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number.") from exc


def _optional_int(value: object, field_name: str) -> int | None:
    number = _optional_float(value, field_name)
    return int(number) if number is not None else None


def render_dashboard(board_data: BoardData, dashboard_df: pd.DataFrame, economics_df: pd.DataFrame, result) -> None:
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
    st.subheader("Economic dashboard")
    econ_cols = st.columns(4)
    econ_cols[0].metric("Total estimated value", _eur(values.get("total_estimated_value", 0)))
    econ_cols[1].metric("Total allocated value", _eur(values.get("total_allocated_value", 0)))
    econ_cols[2].metric("Remaining value", _eur(values.get("remaining_allocated_value_from_today", 0)))
    econ_cols[3].metric("If finished today", _eur(values.get("if_finished_today.remaining_allocated_value", 0)))
    show_dataframe_or_empty(economics_df, "No economic activity rows yet.")


def render_people_editor(board_data: BoardData) -> list[Person] | None:
    df = pd.DataFrame([p.__dict__ for p in board_data.people], columns=["person_id", "name", "hours_per_day", "active"])
    edited = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        height=360,
        column_config=people_column_config(),
    )
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
    columns = ["activity_id", "order", "name", "estimated_days", "estimated_hours", "max_hours_per_day", "daily_price", "status", "notes", "price_notes"]
    df = pd.DataFrame(
        [
            {
                "activity_id": a.activity_id,
                "order": a.order,
                "name": a.name,
                "estimated_days": a.estimated_days if a.estimated_days is not None else (a.estimated_hours / 8 if a.estimated_hours else None),
                "estimated_hours": a.estimated_hours,
                "max_hours_per_day": a.max_hours_per_day,
                "daily_price": a.daily_price if a.daily_price is not None else 0,
                "status": a.status,
                "notes": a.notes,
                "price_notes": a.price_notes,
            }
            for a in board_data.activities
        ],
        columns=columns,
    )
    editor_df = df.copy()
    for column in ["estimated_days", "estimated_hours"]:
        editor_df[column] = editor_df[column].map(format_editable_number).astype("string")
    edited = st.data_editor(
        editor_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        height=420,
        column_config=activity_column_config(),
        key="activities_editor",
    )
    if st.button("Save activities", type="primary"):
        try:
            rows: list[Activity] = []
            for _, row in edited.iterrows():
                if not any(pd.notna(row.get(column)) and str(row.get(column)).strip() != "" for column in edited.columns):
                    continue
                activity_id = str(row.get("activity_id", "")).strip()
                estimated_days, estimated_hours, warnings = normalize_estimates(activity_id, row.get("estimated_days"), row.get("estimated_hours"))
                for warning in warnings:
                    st.warning(warning.message)
                rows.append(
                    Activity(
                        activity_id=activity_id,
                        order=_optional_int(row.get("order"), "order"),
                        name=str(row.get("name", "")).strip(),
                        estimated_hours=estimated_hours,
                        max_hours_per_day=_optional_float(row.get("max_hours_per_day"), "max_hours_per_day"),
                        status=str(row.get("status") or "PLANNED").strip().upper(),
                        notes=str(row.get("notes") or "").strip(),
                        estimated_days=estimated_days,
                        daily_price=_optional_float(row.get("daily_price"), "daily_price"),
                        price_notes=str(row.get("price_notes") or "").strip(),
                    )
                )
            return rows
        except Exception as exc:
            st.session_state["activities_editor_validation_failed"] = True
            st.error(f"Activities could not be saved: {exc}")
    return None


def render_assignments_editor(board_data: BoardData) -> list[Assignment] | None:
    planned_ids = planned_activity_options(board_data)
    active_ids = active_person_options(board_data)
    labels_by_id = person_label_map(board_data)
    ids_by_label = {label: person_id for person_id, label in labels_by_id.items()}
    current: dict[str, list[str]] = {activity_id: [] for activity_id in planned_ids}
    for assignment in board_data.assignments:
        if assignment.activity_id in current and assignment.person_id in active_ids:
            current[assignment.activity_id].append(assignment.person_id)

    st.subheader("Assignments by planned activity")
    selected_by_activity: dict[str, list[str]] = {}
    for activity in [a for a in board_data.activities if a.activity_id in planned_ids]:
        label = f"{activity.activity_id} - {activity.name} ({activity.estimated_hours:g}h)"
        default_labels = [labels_by_id[person_id] for person_id in current.get(activity.activity_id, []) if person_id in labels_by_id]
        selected_labels = st.multiselect(
            label,
            options=list(ids_by_label.keys()),
            default=default_labels,
            key=f"assign_{activity.activity_id}",
        )
        selected_by_activity[activity.activity_id] = [ids_by_label[label] for label in selected_labels]

    if st.button("Save assignments", type="primary"):
        return assignments_from_activity_people(selected_by_activity, board_data)

    with st.expander("Advanced raw assignment table"):
        df = pd.DataFrame([a.__dict__ for a in board_data.assignments], columns=["activity_id", "person_id"])
        edited = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            height=320,
            column_config=raw_assignment_column_config(planned_ids, active_ids),
        )
        if st.button("Save raw assignments"):
            return [
                Assignment(activity_id=str(row.get("activity_id", "")).strip(), person_id=str(row.get("person_id", "")).strip())
                for _, row in edited.iterrows()
                if any(pd.notna(row.get(column)) and str(row.get(column)).strip() != "" for column in edited.columns)
            ]
    return None


def _calendar_row_style(row: pd.Series) -> list[str]:
    if row.get("day_type") in {"WEEKEND", "HOLIDAY", "WEEKEND_HOLIDAY"}:
        return ["background-color: #ffe5e5; color: #9b1c1c"] * len(row)
    return [""] * len(row)


def render_calendar(calendar_df: pd.DataFrame, board_data: BoardData) -> None:
    st.subheader("Pivot calendar")
    pivot_df = build_calendar_pivot_dataframe(calendar_df, board_data)
    if pivot_df.empty:
        st.info("No calendar allocations yet.")
    else:
        person_ids = [p.person_id for p in board_data.people if p.active]
        st.dataframe(
            pivot_df.style.apply(_calendar_row_style, axis=1),
            use_container_width=True,
            hide_index=True,
            height=460,
            column_config=calendar_column_config(person_ids),
        )
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
        f"`05_Calendar`, `06_Dashboard`, `07_Warnings`, and `08_Activity_Economics` are generated by the app. "
        f"Edit `{BOARD_SHEET}`, `{PEOPLE_SHEET}`, `{ACTIVITIES_SHEET}`, and `{ASSIGNMENTS_SHEET}` directly only if you want to work in Excel."
    )
