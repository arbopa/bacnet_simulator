from __future__ import annotations

import math
import random
from dataclasses import dataclass

from app.models.object_model import BehaviorMode, ObjectModel


@dataclass
class BehaviorContext:
    elapsed_seconds: float
    now_seconds: float


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def apply_behavior(point: ObjectModel, linked_value, context: BehaviorContext):
    mode = point.behavior.mode
    if mode in (BehaviorMode.CONSTANT, BehaviorMode.MANUAL, BehaviorMode.LOGIC, BehaviorMode.SCHEDULE):
        return point.present_value

    if mode == BehaviorMode.RANDOM:
        base = float(point.present_value)
        base += random.uniform(-point.behavior.noise, point.behavior.noise)
        return clamp(base, point.behavior.min_value, point.behavior.max_value)

    if mode == BehaviorMode.SINE:
        period = max(point.behavior.period_seconds, 1.0)
        phase = (2.0 * math.pi * context.now_seconds) / period
        center = float(point.initial_value)
        next_value = center + point.behavior.amplitude * math.sin(phase)
        return clamp(next_value, point.behavior.min_value, point.behavior.max_value)

    if mode == BehaviorMode.LINKED and linked_value is not None:
        try:
            current = float(point.present_value)
            target = float(linked_value)
            lag = min(1.0, context.elapsed_seconds / 5.0)
            return current + (target - current) * lag
        except (TypeError, ValueError):
            return linked_value

    return point.present_value
