from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .object_model import ObjectModel


@dataclass
class DeviceModel:
    name: str
    device_instance: int
    vendor_id: int = 999
    description: str = ""
    enabled: bool = True
    bacnet_ip: str = "0.0.0.0"
    bacnet_port: int = 47808
    objects: List[ObjectModel] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "device_instance": self.device_instance,
            "vendor_id": self.vendor_id,
            "description": self.description,
            "enabled": self.enabled,
            "bacnet_ip": self.bacnet_ip,
            "bacnet_port": self.bacnet_port,
            "objects": [obj.to_dict() for obj in self.objects],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceModel":
        return cls(
            name=str(data["name"]),
            device_instance=int(data["device_instance"]),
            vendor_id=int(data.get("vendor_id", 999)),
            description=str(data.get("description", "")),
            enabled=bool(data.get("enabled", True)),
            bacnet_ip=str(data.get("bacnet_ip", "0.0.0.0")),
            bacnet_port=int(data.get("bacnet_port", 47808)),
            objects=[ObjectModel.from_dict(raw) for raw in data.get("objects", [])],
        )

    def get_object(self, object_name: str) -> Optional[ObjectModel]:
        for obj in self.objects:
            if obj.name == object_name:
                return obj
        return None

    def add_object(self, obj: ObjectModel) -> None:
        self.objects.append(obj)

    def remove_object(self, object_name: str) -> None:
        self.objects = [obj for obj in self.objects if obj.name != object_name]

    @property
    def object_count(self) -> int:
        return len(self.objects)
