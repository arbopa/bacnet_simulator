from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable, Dict, List, Set

from app.models.project_model import ProjectModel

from .runtime_point import RuntimePoint

PointSubscriber = Callable[[RuntimePoint], None]


@dataclass
class PointRegistry:
    by_ref: Dict[str, RuntimePoint] = field(default_factory=dict)
    dirty_points: Set[str] = field(default_factory=set)
    subscribers: Dict[str, List[PointSubscriber]] = field(default_factory=dict)
    active_consumers: Set[str] = field(default_factory=set)
    _pending_consumers: Dict[str, Set[str]] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, repr=False, compare=False)

    @classmethod
    def from_project(cls, project: ProjectModel) -> "PointRegistry":
        registry = cls()
        registry.rebuild(project)
        return registry

    def rebuild(self, project: ProjectModel) -> None:
        with self._lock:
            self.by_ref.clear()
            self.dirty_points.clear()
            self._pending_consumers.clear()
            for device in project.devices:
                for point in device.objects:
                    runtime_point = RuntimePoint.from_model(device, point)
                    self.by_ref[runtime_point.ref] = runtime_point

    def set_active_consumers(self, consumers: Set[str]) -> None:
        with self._lock:
            self.active_consumers = set(consumers)
            self._pending_consumers.clear()
            if not self.active_consumers:
                return
            for point_ref in self.dirty_points:
                self._pending_consumers[point_ref] = set(self.active_consumers)

    def get(self, point_ref: str) -> RuntimePoint | None:
        with self._lock:
            return self.by_ref.get(point_ref)

    def set_value(self, point_ref: str, value: Any, *, mark_dirty: bool = True, sync_model: bool = True) -> bool:
        callbacks: List[PointSubscriber] = []
        runtime_point: RuntimePoint | None = None

        with self._lock:
            runtime_point = self.by_ref.get(point_ref)
            if runtime_point is None:
                return False
            changed = runtime_point.set_value(value, mark_dirty=mark_dirty, sync_model=sync_model)
            if not changed:
                return False

            if mark_dirty:
                self.dirty_points.add(runtime_point.ref)
                if self.active_consumers:
                    self._pending_consumers[runtime_point.ref] = set(self.active_consumers)

            callbacks = list(self.subscribers.get(runtime_point.ref, []))

        for callback in callbacks:
            callback(runtime_point)
        return True

    def claim_dirty_for(self, consumer: str) -> List[str]:
        with self._lock:
            if not self.dirty_points:
                return []
            if not self.active_consumers:
                return list(self.dirty_points)
            if consumer not in self.active_consumers:
                return []
            return [
                point_ref
                for point_ref, pending in self._pending_consumers.items()
                if consumer in pending
            ]

    def mark_consumed(self, consumer: str, point_ref: str) -> None:
        with self._lock:
            runtime_point = self.by_ref.get(point_ref)
            if runtime_point is None:
                self.dirty_points.discard(point_ref)
                self._pending_consumers.pop(point_ref, None)
                return

            if point_ref not in self.dirty_points:
                runtime_point.dirty = False
                self._pending_consumers.pop(point_ref, None)
                return

            if not self.active_consumers:
                runtime_point.dirty = False
                self.dirty_points.discard(point_ref)
                self._pending_consumers.pop(point_ref, None)
                return

            pending = self._pending_consumers.setdefault(point_ref, set(self.active_consumers))
            pending.discard(consumer)
            if not pending:
                runtime_point.dirty = False
                self.dirty_points.discard(point_ref)
                self._pending_consumers.pop(point_ref, None)

    def mark_clean(self, point_ref: str) -> None:
        with self._lock:
            runtime_point = self.by_ref.get(point_ref)
            if runtime_point is None:
                return
            runtime_point.dirty = False
            self.dirty_points.discard(point_ref)
            self._pending_consumers.pop(point_ref, None)
    def mark_dirty(self, point_ref: str) -> bool:
        with self._lock:
            runtime_point = self.by_ref.get(point_ref)
            if runtime_point is None:
                return False
            runtime_point.dirty = True
            self.dirty_points.add(point_ref)
            if self.active_consumers:
                self._pending_consumers[point_ref] = set(self.active_consumers)
            return True
    def mark_all_clean(self) -> None:
        with self._lock:
            point_refs = list(self.dirty_points)
        for point_ref in point_refs:
            self.mark_clean(point_ref)

    def dirty_point_refs(self) -> List[str]:
        with self._lock:
            return list(self.dirty_points)

    def subscribe(self, point_ref: str, callback: PointSubscriber) -> None:
        with self._lock:
            callbacks = self.subscribers.setdefault(point_ref, [])
            if callback not in callbacks:
                callbacks.append(callback)

    def unsubscribe(self, point_ref: str, callback: PointSubscriber) -> None:
        with self._lock:
            callbacks = self.subscribers.get(point_ref)
            if not callbacks:
                return
            self.subscribers[point_ref] = [item for item in callbacks if item != callback]
            if not self.subscribers[point_ref]:
                self.subscribers.pop(point_ref, None)
