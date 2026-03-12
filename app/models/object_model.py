from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ObjectType(str, Enum):
    DEVICE = "device"
    ANALOG_INPUT = "analogInput"
    ANALOG_OUTPUT = "analogOutput"
    ANALOG_VALUE = "analogValue"
    BINARY_INPUT = "binaryInput"
    BINARY_OUTPUT = "binaryOutput"
    BINARY_VALUE = "binaryValue"
    MULTI_STATE_VALUE = "multiStateValue"
    SCHEDULE = "schedule"
    TREND_LOG = "trendLog"


class BehaviorMode(str, Enum):
    CONSTANT = "constant"
    MANUAL = "manual"
    RANDOM = "random"
    SINE = "sine"
    LINKED = "linked"
    LOGIC = "logic"
    SCHEDULE = "schedule"


@dataclass
class BehaviorConfig:
    mode: BehaviorMode = BehaviorMode.MANUAL
    amplitude: float = 1.0
    period_seconds: float = 120.0
    noise: float = 0.2
    linked_point_ref: str = ""
    min_value: float = 0.0
    max_value: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "amplitude": self.amplitude,
            "period_seconds": self.period_seconds,
            "noise": self.noise,
            "linked_point_ref": self.linked_point_ref,
            "min_value": self.min_value,
            "max_value": self.max_value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BehaviorConfig":
        return cls(
            mode=BehaviorMode(data.get("mode", BehaviorMode.MANUAL.value)),
            amplitude=float(data.get("amplitude", 1.0)),
            period_seconds=float(data.get("period_seconds", 120.0)),
            noise=float(data.get("noise", 0.2)),
            linked_point_ref=str(data.get("linked_point_ref", "")),
            min_value=float(data.get("min_value", 0.0)),
            max_value=float(data.get("max_value", 100.0)),
        )


@dataclass
class ScheduleConfig:
    # HH:MM local-time weekday schedule
    weekday_start: str = "06:00"
    weekday_end: str = "18:00"
    occupied_value: float = 1.0
    unoccupied_value: float = 0.0
    schedule_ref: str = ""  # optional external schedule object ref

    def to_dict(self) -> Dict[str, Any]:
        return {
            "weekday_start": self.weekday_start,
            "weekday_end": self.weekday_end,
            "occupied_value": self.occupied_value,
            "unoccupied_value": self.unoccupied_value,
            "schedule_ref": self.schedule_ref,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduleConfig":
        return cls(
            weekday_start=str(data.get("weekday_start", "06:00")),
            weekday_end=str(data.get("weekday_end", "18:00")),
            occupied_value=float(data.get("occupied_value", 1.0)),
            unoccupied_value=float(data.get("unoccupied_value", 0.0)),
            schedule_ref=str(data.get("schedule_ref", "")),
        )


@dataclass
class ObjectModel:
    instance: int
    name: str
    object_type: ObjectType
    description: str = ""
    units: str = ""
    present_value: Any = 0.0
    initial_value: Any = 0.0
    writable: bool = False
    out_of_service: bool = False
    cov_increment: float = 0.5
    relinquish_default: Any = 0.0
    priority_array: List[Optional[Any]] = field(default_factory=lambda: [None] * 16)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance": self.instance,
            "name": self.name,
            "object_type": self.object_type.value,
            "description": self.description,
            "units": self.units,
            "present_value": self.present_value,
            "initial_value": self.initial_value,
            "writable": self.writable,
            "out_of_service": self.out_of_service,
            "cov_increment": self.cov_increment,
            "relinquish_default": self.relinquish_default,
            "priority_array": self.priority_array,
            "behavior": self.behavior.to_dict(),
            "schedule": self.schedule.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjectModel":
        source_priority = list(data.get("priority_array", [None] * 16))[:16]
        return cls(
            instance=int(data["instance"]),
            name=str(data["name"]),
            object_type=ObjectType(data["object_type"]),
            description=str(data.get("description", "")),
            units=str(data.get("units", "")),
            present_value=data.get("present_value", 0.0),
            initial_value=data.get("initial_value", data.get("present_value", 0.0)),
            writable=bool(data.get("writable", False)),
            out_of_service=bool(data.get("out_of_service", False)),
            cov_increment=float(data.get("cov_increment", 0.5)),
            relinquish_default=data.get("relinquish_default", 0.0),
            priority_array=source_priority + [None] * (16 - len(source_priority)),
            behavior=BehaviorConfig.from_dict(data.get("behavior", {})),
            schedule=ScheduleConfig.from_dict(data.get("schedule", {})),
            metadata=dict(data.get("metadata", {})),
        )

    def object_ref(self, device_name: str) -> str:
        return f"{device_name}.{self.name}"

    def effective_value(self) -> Any:
        for value in self.priority_array:
            if value is not None:
                return value
        return self.present_value if self.present_value is not None else self.relinquish_default

    def write_with_priority(self, value: Any, priority: int = 16) -> None:
        if not self.writable:
            return
        index = min(max(priority, 1), 16) - 1
        self.priority_array[index] = value
        self.present_value = self.effective_value()

    def relinquish_priority(self, priority: int = 16) -> None:
        index = min(max(priority, 1), 16) - 1
        self.priority_array[index] = None
        self.present_value = self.effective_value()
