from __future__ import annotations

from datetime import datetime

from app.models.object_model import ObjectModel


def _to_minutes(hhmm: str) -> int:
    parts = hhmm.split(":", 1)
    if len(parts) != 2:
        return 0
    try:
        h = max(0, min(23, int(parts[0])))
        m = max(0, min(59, int(parts[1])))
    except ValueError:
        return 0
    return h * 60 + m


def schedule_value(schedule_obj: ObjectModel, now: datetime | None = None) -> float:
    now = now or datetime.now()
    if now.weekday() >= 5:  # Sat/Sun
        return schedule_obj.schedule.unoccupied_value

    current = now.hour * 60 + now.minute
    start = _to_minutes(schedule_obj.schedule.weekday_start)
    end = _to_minutes(schedule_obj.schedule.weekday_end)
    if start <= current < end:
        return schedule_obj.schedule.occupied_value
    return schedule_obj.schedule.unoccupied_value
