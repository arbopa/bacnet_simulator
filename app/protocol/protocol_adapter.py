from __future__ import annotations

from typing import Protocol

from app.models.project_model import ProjectModel
from app.runtime import PointRegistry


class ProtocolAdapter(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def available(self) -> bool:
        ...

    def set_project(self, project: ProjectModel) -> None:
        ...

    def set_registry(self, registry: PointRegistry | None) -> None:
        ...

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def notify_simulation_tick(self) -> None:
        ...
