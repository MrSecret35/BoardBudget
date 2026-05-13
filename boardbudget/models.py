from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class BoardSettings:
    board_name: str
    start_date: date
    hours_per_day: float = 8.0
    working_days: tuple[str, ...] = ("MON", "TUE", "WED", "THU", "FRI")


@dataclass
class Person:
    person_id: str
    name: str
    hours_per_day: float | None = None
    active: bool = True


@dataclass
class Activity:
    activity_id: str
    order: int | None
    name: str
    estimated_hours: float
    max_hours_per_day: float | None = None
    status: str = "PLANNED"
    notes: str = ""


@dataclass(frozen=True)
class Assignment:
    activity_id: str
    person_id: str


@dataclass
class CalendarAllocation:
    date: date
    person_id: str
    person_name: str
    activity_id: str
    activity_name: str
    hours: float


@dataclass
class WarningMessage:
    level: str
    code: str
    message: str


@dataclass
class BoardData:
    settings: BoardSettings
    people: list[Person] = field(default_factory=list)
    activities: list[Activity] = field(default_factory=list)
    assignments: list[Assignment] = field(default_factory=list)
    warnings: list[WarningMessage] = field(default_factory=list)

