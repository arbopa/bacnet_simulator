from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .device_model import DeviceModel


@dataclass
class BacnetSettings:
    network_name: str = "SimNetwork"
    bind_ip: str = "0.0.0.0"
    base_udp_port: int = 47808
    interface_alias: str = ""
    auto_manage_ip_aliases: bool = False
    alias_prefix_length: int = 24
    remove_auto_aliases_on_exit: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "network_name": self.network_name,
            "bind_ip": self.bind_ip,
            "base_udp_port": self.base_udp_port,
            "interface_alias": self.interface_alias,
            "auto_manage_ip_aliases": self.auto_manage_ip_aliases,
            "alias_prefix_length": self.alias_prefix_length,
            "remove_auto_aliases_on_exit": self.remove_auto_aliases_on_exit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacnetSettings":
        return cls(
            network_name=str(data.get("network_name", "SimNetwork")),
            bind_ip=str(data.get("bind_ip", "0.0.0.0")),
            base_udp_port=int(data.get("base_udp_port", 47808)),
            interface_alias=str(data.get("interface_alias", "")),
            auto_manage_ip_aliases=bool(data.get("auto_manage_ip_aliases", False)),
            alias_prefix_length=int(data.get("alias_prefix_length", 24)),
            remove_auto_aliases_on_exit=bool(data.get("remove_auto_aliases_on_exit", False)),
        )


@dataclass
class LogicRule:
    name: str
    lhs_ref: str
    operator: str
    rhs_value: Any
    action_ref: str
    action_value: Any
    else_value: Any = None
    delay_seconds: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "lhs_ref": self.lhs_ref,
            "operator": self.operator,
            "rhs_value": self.rhs_value,
            "action_ref": self.action_ref,
            "action_value": self.action_value,
            "else_value": self.else_value,
            "delay_seconds": self.delay_seconds,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogicRule":
        return cls(
            name=str(data["name"]),
            lhs_ref=str(data["lhs_ref"]),
            operator=str(data.get("operator", "==")),
            rhs_value=data.get("rhs_value"),
            action_ref=str(data["action_ref"]),
            action_value=data.get("action_value"),
            else_value=data.get("else_value"),
            delay_seconds=float(data.get("delay_seconds", 0.0)),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass
class ScenarioState:
    occupied: bool = True
    outdoor_air_temp: float = 55.0
    alarm_injection: bool = False
    sensor_failure_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "occupied": self.occupied,
            "outdoor_air_temp": self.outdoor_air_temp,
            "alarm_injection": self.alarm_injection,
            "sensor_failure_refs": list(self.sensor_failure_refs),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioState":
        return cls(
            occupied=bool(data.get("occupied", True)),
            outdoor_air_temp=float(data.get("outdoor_air_temp", 55.0)),
            alarm_injection=bool(data.get("alarm_injection", False)),
            sensor_failure_refs=list(data.get("sensor_failure_refs", [])),
        )


@dataclass
class ProjectModel:
    name: str = "New BAS Project"
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    bacnet: BacnetSettings = field(default_factory=BacnetSettings)
    devices: List[DeviceModel] = field(default_factory=list)
    logic_rules: List[LogicRule] = field(default_factory=list)
    scenario: ScenarioState = field(default_factory=ScenarioState)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "bacnet": self.bacnet.to_dict(),
            "devices": [device.to_dict() for device in self.devices],
            "logic_rules": [rule.to_dict() for rule in self.logic_rules],
            "scenario": self.scenario.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectModel":
        return cls(
            name=str(data.get("name", "New BAS Project")),
            description=str(data.get("description", "")),
            created_at=str(data.get("created_at", datetime.utcnow().isoformat())),
            bacnet=BacnetSettings.from_dict(data.get("bacnet", {})),
            devices=[DeviceModel.from_dict(raw) for raw in data.get("devices", [])],
            logic_rules=[LogicRule.from_dict(raw) for raw in data.get("logic_rules", [])],
            scenario=ScenarioState.from_dict(data.get("scenario", {})),
        )

    def get_device(self, name: str) -> Optional[DeviceModel]:
        for device in self.devices:
            if device.name == name:
                return device
        return None

    def get_point_by_ref(self, point_ref: str):
        try:
            device_name, point_name = point_ref.split(".", 1)
        except ValueError:
            return None
        device = self.get_device(device_name)
        if not device:
            return None
        return device.get_object(point_name)

    def all_point_refs(self) -> List[str]:
        refs: List[str] = []
        for device in self.devices:
            for obj in device.objects:
                refs.append(f"{device.name}.{obj.name}")
        return refs
