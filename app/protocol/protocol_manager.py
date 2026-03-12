from __future__ import annotations

from typing import List

from PySide6.QtCore import QObject, Signal

from app.models.project_model import ProjectModel
from app.runtime import PointRegistry

from .protocol_adapter import ProtocolAdapter


class ProtocolManager(QObject):
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._adapters: List[ProtocolAdapter] = []
        self._registry: PointRegistry | None = None

    def _active_consumer_names(self) -> set[str]:
        return {adapter.name for adapter in self._adapters if adapter.available}

    def _sync_registry_consumers(self) -> None:
        if self._registry is None:
            return
        self._registry.set_active_consumers(self._active_consumer_names())

    def register_adapter(self, adapter: ProtocolAdapter) -> None:
        self._adapters.append(adapter)
        adapter_message = getattr(adapter, "message", None)
        if adapter_message is not None:
            adapter_message.connect(self.message.emit)
        self._sync_registry_consumers()

    def set_project(self, project: ProjectModel) -> None:
        for adapter in self._adapters:
            adapter.set_project(project)

    def set_registry(self, registry: PointRegistry | None) -> None:
        self._registry = registry
        for adapter in self._adapters:
            adapter.set_registry(registry)
        self._sync_registry_consumers()

    def start(self) -> None:
        self._sync_registry_consumers()
        for adapter in self._adapters:
            if not adapter.available:
                self.message.emit(f"[{adapter.name}] unavailable in current environment")
                continue
            adapter.start()

    def stop(self) -> None:
        for adapter in self._adapters:
            adapter.stop()

    def notify_simulation_tick(self) -> None:
        for adapter in self._adapters:
            adapter.notify_simulation_tick()
