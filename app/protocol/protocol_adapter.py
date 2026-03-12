from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.project_model import ProjectModel
from app.runtime import PointRegistry


class ProtocolAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def available(self) -> bool:
        ...

    @abstractmethod
    def set_project(self, project: ProjectModel) -> None:
        ...

    @abstractmethod
    def set_registry(self, registry: PointRegistry | None) -> None:
        ...

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def notify_simulation_tick(self) -> None:
        ...
