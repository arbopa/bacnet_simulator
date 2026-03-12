from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Deque, Dict, List, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from app.models.object_model import BehaviorMode, ObjectType
from app.models.project_model import ProjectModel
from app.sim.behaviors import BehaviorContext, apply_behavior
from app.sim.logic_engine import LogicEngine
from app.sim.scenarios import apply_scenario
from app.sim.schedule_engine import schedule_value


class SimulationEngine(QObject):
    tick_completed = Signal(dict)
    started = Signal()
    stopped = Signal()
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project: ProjectModel | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._interval_ms = 1000
        self._running = False
        self._paused = False
        self._last_time = time.monotonic()
        self.logic = LogicEngine()
        self.trends: Dict[str, Deque[Tuple[float, float]]] = defaultdict(lambda: deque(maxlen=1800))
        self.trend_logs: Dict[str, Deque[Tuple[float, float]]] = defaultdict(lambda: deque(maxlen=3600))

    @property
    def running(self) -> bool:
        return self._running and not self._paused

    def set_project(self, project: ProjectModel) -> None:
        self._project = project

    def set_interval_ms(self, interval_ms: int) -> None:
        self._interval_ms = max(100, interval_ms)
        if self._timer.isActive():
            self._timer.start(self._interval_ms)

    def start(self) -> None:
        if self._project is None:
            self.message.emit("No project loaded.")
            return
        if self._running:
            return
        self._running = True
        self._paused = False
        self._last_time = time.monotonic()
        self._timer.start(self._interval_ms)
        self.started.emit()
        self.message.emit("Simulation started.")

    def stop(self) -> None:
        self._timer.stop()
        self._running = False
        self._paused = False
        self.stopped.emit()
        self.message.emit("Simulation stopped.")

    def pause(self) -> None:
        if not self._running:
            return
        self._paused = True
        self.message.emit("Simulation paused.")

    def resume(self) -> None:
        if not self._running:
            return
        self._paused = False
        self.message.emit("Simulation resumed.")

    def reset_values(self) -> None:
        if self._project is None:
            return
        for device in self._project.devices:
            for point in device.objects:
                point.present_value = point.initial_value
                point.priority_array = [None] * 16
        self.message.emit("All point values reset to initial values.")

    def _tick(self) -> None:
        if not self._running or self._paused or self._project is None:
            return

        now_monotonic = time.monotonic()
        elapsed = max(0.001, now_monotonic - self._last_time)
        self._last_time = now_monotonic
        now_real = time.time()
        now_dt = datetime.now()
        context = BehaviorContext(elapsed_seconds=elapsed, now_seconds=now_monotonic)

        apply_scenario(self._project)
        self.logic.evaluate(self._project)

        # 1) Evaluate schedule objects first.
        for device in self._project.devices:
            for point in device.objects:
                if point.object_type == ObjectType.SCHEDULE:
                    point.present_value = schedule_value(point, now_dt)

        snapshot: Dict[str, float] = {}

        # 2) Evaluate point behaviors and linked values.
        for device in self._project.devices:
            for point in device.objects:
                if point.object_type in {ObjectType.SCHEDULE, ObjectType.TREND_LOG}:
                    continue

                linked_value = None
                if point.behavior.linked_point_ref:
                    linked = self._project.get_point_by_ref(point.behavior.linked_point_ref)
                    if linked is not None:
                        linked_value = linked.present_value

                if point.behavior.mode == BehaviorMode.SCHEDULE:
                    schedule_ref = point.schedule.schedule_ref or point.behavior.linked_point_ref
                    if schedule_ref:
                        schedule_obj = self._project.get_point_by_ref(schedule_ref)
                        if schedule_obj is not None:
                            point.present_value = schedule_obj.present_value
                    else:
                        # local embedded schedule when no separate schedule object is linked
                        synthetic = schedule_value(point, now_dt)
                        point.present_value = synthetic
                else:
                    point.present_value = apply_behavior(point, linked_value, context)

                ref = point.object_ref(device.name)
                try:
                    numeric = float(point.present_value)
                    self.trends[ref].append((now_real, numeric))
                    snapshot[ref] = numeric
                except (TypeError, ValueError):
                    pass

        # 3) Evaluate trend log objects from source references.
        for device in self._project.devices:
            for point in device.objects:
                if point.object_type != ObjectType.TREND_LOG:
                    continue
                source_ref = str(point.metadata.get("source_ref", "")).strip()
                if not source_ref:
                    continue
                source = self._project.get_point_by_ref(source_ref)
                if source is None:
                    continue
                try:
                    value = float(source.present_value)
                except (TypeError, ValueError):
                    continue
                trend_ref = point.object_ref(device.name)
                self.trend_logs[trend_ref].append((now_real, value))
                point.present_value = value
                self.trends[trend_ref].append((now_real, value))
                snapshot[trend_ref] = value

        self.tick_completed.emit(snapshot)

    def get_trend(self, point_ref: str, last_n: int = 300) -> List[Tuple[float, float]]:
        samples = self.trends.get(point_ref, deque())
        if last_n <= 0:
            return list(samples)
        return list(samples)[-last_n:]

    def get_trend_log(self, trend_ref: str, last_n: int = 300) -> List[Tuple[float, float]]:
        samples = self.trend_logs.get(trend_ref, deque())
        if last_n <= 0:
            return list(samples)
        return list(samples)[-last_n:]
