from __future__ import annotations

import pandas as pd
import streamlit as st

from boardbudget.config import ALLOWED_STATUSES


def show_dataframe_or_empty(df: pd.DataFrame, empty_message: str) -> None:
    if df.empty:
        st.info(empty_message)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def status_column_config() -> dict[str, object]:
    return {
        "status": st.column_config.SelectboxColumn(
            "status",
            options=list(ALLOWED_STATUSES),
            required=True,
        )
    }

