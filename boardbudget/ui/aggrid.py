from __future__ import annotations

import pandas as pd
import streamlit as st


def _safe_hex_color(color: str) -> str:
    if isinstance(color, str) and len(color) == 7 and color.startswith("#"):
        return color
    return "#fdecec"


def build_grid_options(
    df: pd.DataFrame,
    column_widths: dict[str, int] | None = None,
    highlight_non_working_days: bool = False,
    highlight_absences: bool = False,
    non_working_day_color: str = "#fdecec",
    absence_day_color: str = "#fff4cc",
    default_sort: tuple[str, str] | None = None,
    pinned_columns: list[str] | None = None,
    bold_columns: list[str] | None = None,
) -> dict:
    from st_aggrid import GridOptionsBuilder, JsCode

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, sortable=True, filter=True, wrapText=False)
    pinned = set(pinned_columns or [])
    bold = set(bold_columns or [])
    for column in df.columns:
        kwargs: dict[str, object] = {}
        if column_widths and column in column_widths:
            kwargs["width"] = column_widths[column]
        if column in pinned:
            kwargs["pinned"] = "left"
        if default_sort and column == default_sort[0]:
            kwargs["sort"] = default_sort[1]
        if column in bold:
            kwargs["cellStyle"] = {"fontWeight": "700"}
        if kwargs:
            gb.configure_column(column, **kwargs)
    options = gb.build()
    options["defaultColDef"]["sortingOrder"] = ["asc", "desc", None]
    options["suppressMultiSort"] = True
    if highlight_non_working_days:
        color = _safe_hex_color(non_working_day_color)
        options["getRowStyle"] = JsCode(
            f"""
            function(params) {{
                if (params.data.day_type === 'WEEKEND' || params.data.day_type === 'HOLIDAY' || params.data.day_type === 'WEEKEND_HOLIDAY') {{
                    return {{ backgroundColor: '{color}', color: '#9f3333' }};
                }}
                return {{}};
            }}
            """
        )
    if highlight_absences:
        absence_color = _safe_hex_color(absence_day_color)
        technical = {"date", "day_name", "day_type", "holiday_name"}
        for col_def in options.get("columnDefs", []):
            if col_def.get("field") not in technical:
                col_def["cellStyle"] = JsCode(
                    f"""
                    function(params) {{
                        if (params.value && String(params.value).indexOf('Absence') >= 0 && String(params.value).indexOf('? Absence') < 0) {{
                            return {{ backgroundColor: '{absence_color}', color: '#6b4f00', fontWeight: '600' }};
                        }}
                        return null;
                    }}
                    """
                )
    return options


def render_grid(
    df: pd.DataFrame,
    key: str,
    height: int = 400,
    column_widths: dict[str, int] | None = None,
    highlight_non_working_days: bool = False,
    highlight_absences: bool = False,
    non_working_day_color: str = "#fdecec",
    absence_day_color: str = "#fff4cc",
    default_sort: tuple[str, str] | None = None,
    pinned_columns: list[str] | None = None,
    bold_columns: list[str] | None = None,
) -> None:
    try:
        from st_aggrid import AgGrid
    except ImportError:
        st.dataframe(df, use_container_width=True, hide_index=True, height=height)
        return

    AgGrid(
        df,
        gridOptions=build_grid_options(
            df,
            column_widths=column_widths,
            highlight_non_working_days=highlight_non_working_days,
            highlight_absences=highlight_absences,
            non_working_day_color=non_working_day_color,
            absence_day_color=absence_day_color,
            default_sort=default_sort,
            pinned_columns=pinned_columns,
            bold_columns=bold_columns,
        ),
        allow_unsafe_jscode=highlight_non_working_days or highlight_absences,
        fit_columns_on_grid_load=False,
        height=height,
        theme="streamlit",
        enable_enterprise_modules=False,
        key=key,
    )


def render_calendar_grid(df: pd.DataFrame, person_ids: list[str], non_working_day_color: str = "#fdecec", absence_day_color: str = "#fff4cc", height: int = 520) -> None:
    widths = {"date": 120, "day_name": 110, "day_type": 110, "holiday_name": 180}
    widths.update({person_id: 320 for person_id in person_ids})
    render_grid(
        df,
        key="calendar_pivot_grid",
        height=height,
        column_widths=widths,
        highlight_non_working_days=True,
        highlight_absences=True,
        non_working_day_color=non_working_day_color,
        absence_day_color=absence_day_color,
        default_sort=("date", "asc"),
        pinned_columns=["date", "day_name"],
        bold_columns=["date", "day_name", *person_ids],
    )


def render_raw_calendar_grid(df: pd.DataFrame, height: int = 360) -> None:
    render_grid(
        df,
        key="calendar_raw_grid",
        height=height,
        column_widths={
            "date": 120,
            "person_id": 120,
            "person_name": 170,
            "activity_id": 120,
            "activity_name": 260,
            "hours": 100,
        },
        default_sort=("date", "asc"),
        pinned_columns=["date"],
        bold_columns=["date"],
    )
