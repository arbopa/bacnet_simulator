from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.bacnet.bacnet_manager import BacnetManager
from app.models.project_model import ProjectModel
from app.runtime import PointRegistry

from .protocol_adapter import ProtocolAdapter


class BacnetProtocolAdapter(QObject, ProtocolAdapter):
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = BacnetManager(parent=self)
        self._manager.status_changed.connect(self._on_status)
        self._manager.error.connect(self._on_error)

    @property
    def name(self) -> str:
        return "bacnet"

    @property
    def available(self) -> bool:
        return self._manager.available

    def set_project(self, project: ProjectModel) -> None:
        self._manager.set_project(project)

    def set_registry(self, registry: PointRegistry | None) -> None:
        self._manager.set_registry(registry)

    def start(self) -> None:
        self._manager.start()

    def stop(self) -> None:
        self._manager.stop()

    def notify_simulation_tick(self) -> None:
        self._manager.notify_simulation_tick()

    def _on_status(self, text: str) -> None:
        self.message.emit(f"[{self.name}] {text}")

    def _on_error(self, text: str) -> None:
        self.message.emit(f"[{self.name}] {text}")
