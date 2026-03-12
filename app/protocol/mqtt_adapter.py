from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.models.project_model import ProjectModel
from app.runtime import PointRegistry

from .protocol_adapter import ProtocolAdapter


class MqttProtocolAdapter(QObject, ProtocolAdapter):
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    @property
    def name(self) -> str:
        return "mqtt"

    @property
    def available(self) -> bool:
        return False

    def set_project(self, project: ProjectModel) -> None:
        _ = project

    def set_registry(self, registry: PointRegistry | None) -> None:
        _ = registry

    def start(self) -> None:
        return

    def stop(self) -> None:
        return

    def notify_simulation_tick(self) -> None:
        return
