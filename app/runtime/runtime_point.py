from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.device_model import DeviceModel
from app.models.object_model import ObjectModel


@dataclass
class RuntimePoint:
    ref: str
    device_name: str
    object_name: str
    model_point: ObjectModel
    model_device: DeviceModel
    current_value: Any
    last_value: Any = None
    dirty: bool = False

    @classmethod
    def from_model(cls, device: DeviceModel, point: ObjectModel) -> "RuntimePoint":
        ref = point.object_ref(device.name)
        value = point.present_value
        return cls(
            ref=ref,
            device_name=device.name,
            object_name=point.name,
            model_point=point,
            model_device=device,
            current_value=value,
            last_value=value,
            dirty=False,
        )

    def set_value(self, value: Any, *, mark_dirty: bool = True, sync_model: bool = True) -> bool:
        changed = value != self.current_value
        if not changed:
            if sync_model:
                self.model_point.present_value = value
            return False

        self.last_value = self.current_value
        self.current_value = value
        if sync_model:
            self.model_point.present_value = value
        if mark_dirty:
            self.dirty = True
        return True

    def refresh_from_model(self, *, mark_dirty: bool = False) -> bool:
        return self.set_value(self.model_point.present_value, mark_dirty=mark_dirty, sync_model=False)
