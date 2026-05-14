from __future__ import annotations

import pandas as pd
import streamlit as st

from boardbudget.config import ALLOWED_STATUSES


def show_dataframe_or_empty(df: pd.DataFrame, empty_message: str) -> None:
    if df.empty:
        st.info(empty_message)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, height=360)


def status_column_config() -> dict[str, object]:
    return {
        "status": st.column_config.SelectboxColumn(
            "status",
            options=list(ALLOWED_STATUSES),
            required=True,
        )
    }


def people_column_config() -> dict[str, object]:
    return {
        "person_id": st.column_config.TextColumn("person_id", width="small"),
        "name": st.column_config.TextColumn("name", width="medium"),
        "hours_per_day": st.column_config.NumberColumn("hours_per_day", width="small"),
        "daily_cost": st.column_config.NumberColumn("daily_cost", width="small"),
        "active": st.column_config.CheckboxColumn("active", width="small"),
    }


def activity_column_config() -> dict[str, object]:
    config = status_column_config()
    config.update(
        {
            "activity_id": st.column_config.TextColumn("activity_id", width="small"),
            "order": st.column_config.NumberColumn("order", width="small"),
            "name": st.column_config.TextColumn("name", width="large"),
            "estimated_days": st.column_config.TextColumn("estimated_days", width="small"),
            "estimated_hours": st.column_config.TextColumn("estimated_hours", width="small"),
            "max_hours_per_day": st.column_config.NumberColumn("max_hours_per_day", width="small"),
            "daily_price": st.column_config.NumberColumn("daily_price", width="small"),
            "notes": st.column_config.TextColumn("notes", width="large"),
            "price_notes": st.column_config.TextColumn("price_notes", width="large"),
        }
    )
    return config


def calendar_column_config(person_ids: list[str]) -> dict[str, object]:
    config: dict[str, object] = {
        "date": st.column_config.TextColumn("date", width="small"),
        "day_name": st.column_config.TextColumn("day_name", width="small"),
        "day_type": st.column_config.TextColumn("day_type", width="medium"),
        "holiday_name": st.column_config.TextColumn("holiday_name", width="large"),
    }
    for person_id in person_ids:
        config[person_id] = st.column_config.TextColumn(person_id, width="large")
    return config


def raw_assignment_column_config(activity_ids: list[str], person_ids: list[str]) -> dict[str, object]:
    return {
        "activity_id": st.column_config.SelectboxColumn("activity_id", options=activity_ids, width="medium"),
        "person_id": st.column_config.SelectboxColumn("person_id", options=person_ids, width="medium"),
    }
