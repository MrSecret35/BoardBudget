from __future__ import annotations

import pandas as pd
import streamlit as st


def render_calendar_grid(df: pd.DataFrame, person_ids: list[str], height: int = 520) -> None:
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
    except ImportError:
        st.dataframe(df, use_container_width=True, hide_index=True, height=height)
        return

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, sortable=True, filter=True, wrapText=True)
    gb.configure_column("date", width=135, pinned="left", cellStyle={"fontWeight": "700"})
    gb.configure_column("day_name", width=130, pinned="left", cellStyle={"fontWeight": "700"})
    gb.configure_column("day_type", width=125)
    gb.configure_column("holiday_name", width=190)
    for person_id in person_ids:
        gb.configure_column(person_id, width=320, minWidth=240, cellStyle={"fontWeight": "600"})

    options = gb.build()
    options["getRowStyle"] = JsCode(
        """
        function(params) {
            if (params.data.day_type === 'WEEKEND' || params.data.day_type === 'HOLIDAY' || params.data.day_type === 'WEEKEND_HOLIDAY') {
                return { backgroundColor: '#ffe5e5', color: '#9b1c1c' };
            }
            return {};
        }
        """
    )

    AgGrid(
        df,
        gridOptions=options,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=False,
        height=height,
        theme="streamlit",
        enable_enterprise_modules=False,
    )


def render_raw_calendar_grid(df: pd.DataFrame, height: int = 360) -> None:
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder
    except ImportError:
        st.dataframe(df, use_container_width=True, hide_index=True, height=height)
        return

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, sortable=True, filter=True, wrapText=True)
    gb.configure_column("date", width=135, pinned="left", cellStyle={"fontWeight": "700"})
    gb.configure_column("person_id", width=120)
    gb.configure_column("person_name", width=170)
    gb.configure_column("activity_id", width=120)
    gb.configure_column("activity_name", width=260)
    gb.configure_column("hours", width=100)

    AgGrid(
        df,
        gridOptions=gb.build(),
        fit_columns_on_grid_load=False,
        height=height,
        theme="streamlit",
        enable_enterprise_modules=False,
    )
