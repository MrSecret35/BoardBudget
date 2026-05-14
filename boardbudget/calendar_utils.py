from __future__ import annotations

from datetime import date

import holidays


def is_weekend(day: date) -> bool:
    return day.weekday() >= 5


def get_italian_holidays_for_years(years: set[int]) -> dict[date, str]:
    if not years:
        return {}
    calendar = holidays.country_holidays("IT", years=sorted(years))
    return {holiday_date: str(name) for holiday_date, name in calendar.items()}


def classify_day(day: date, holidays_map: dict[date, str]) -> tuple[str, str]:
    weekend = is_weekend(day)
    holiday_name = holidays_map.get(day, "")
    holiday = bool(holiday_name)
    if weekend and holiday:
        return "WEEKEND_HOLIDAY", holiday_name
    if weekend:
        return "WEEKEND", ""
    if holiday:
        return "HOLIDAY", holiday_name
    return "WORKING_DAY", ""

