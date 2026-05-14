from __future__ import annotations

from .config import STATUS_PLANNED
from .models import Assignment, BoardData


def planned_activity_options(board_data: BoardData) -> list[str]:
    return [activity.activity_id for activity in board_data.activities if activity.status == STATUS_PLANNED and activity.activity_id]


def active_person_options(board_data: BoardData) -> list[str]:
    return [person.person_id for person in board_data.people if person.active and person.person_id]


def person_label_map(board_data: BoardData) -> dict[str, str]:
    return {person.person_id: f"{person.person_id} - {person.name}" for person in board_data.people if person.active and person.person_id}


def assignments_from_activity_people(activity_people: dict[str, list[str]], board_data: BoardData) -> list[Assignment]:
    planned = set(planned_activity_options(board_data))
    active = set(active_person_options(board_data))
    assignments: list[Assignment] = []
    seen: set[tuple[str, str]] = set()
    for activity_id in sorted(activity_people):
        if activity_id not in planned:
            continue
        for person_id in activity_people[activity_id]:
            pair = (activity_id, person_id)
            if person_id in active and pair not in seen:
                assignments.append(Assignment(activity_id=activity_id, person_id=person_id))
                seen.add(pair)
    return assignments

