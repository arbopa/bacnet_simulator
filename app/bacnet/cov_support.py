from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class COVTracker:
    last_values: Dict[str, float]

    def __init__(self):
        self.last_values = {}

    def changed(self, point_ref: str, value: float, increment: float) -> bool:
        old = self.last_values.get(point_ref)
        if old is None:
            self.last_values[point_ref] = value
            return True
        if abs(value - old) >= max(0.0001, increment):
            self.last_values[point_ref] = value
            return True
        return False
