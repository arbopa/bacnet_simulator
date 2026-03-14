from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Deque, Dict, List, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from app.models.object_model import BehaviorMode, ObjectModel, ObjectType
from app.models.project_model import ProjectModel
from app.runtime import PointRegistry, RuntimePoint
from app.sim.behaviors import BehaviorContext, apply_behavior
from app.sim.logic_engine import LogicEngine
from app.sim.response_engine import compute_response
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
        self.registry = PointRegistry()
        self.trends: Dict[str, Deque[Tuple[float, float]]] = defaultdict(lambda: deque(maxlen=1800))
        self.trend_logs: Dict[str, Deque[Tuple[float, float]]] = defaultdict(lambda: deque(maxlen=3600))

    @property
    def running(self) -> bool:
        return self._running and not self._paused

    def set_project(self, project: ProjectModel) -> None:
        self._project = project
        self.rebuild_runtime_registry()

    def rebuild_runtime_registry(self) -> None:
        if self._project is None:
            self.registry = PointRegistry()
            return
        self.registry.rebuild(self._project)

    def get_runtime_point(self, point_ref: str) -> RuntimePoint | None:
        return self.registry.get(point_ref)

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
                self.registry.set_value(point.object_ref(device.name), point.initial_value, sync_model=False)
        self.message.emit("All point values reset to initial values.")

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _clamp(value: float, min_value: float, max_value: float) -> float:
        if max_value < min_value:
            min_value, max_value = max_value, min_value
        return max(min_value, min(max_value, value))

    def _resolve_point_value(self, point_ref: str) -> float | None:
        if self._project is None:
            return None
        source = self._project.get_point_by_ref(point_ref)
        if source is None:
            return None
        try:
            return float(source.present_value)
        except (TypeError, ValueError):
            return None

    def _evaluate_response(self, point: ObjectModel, elapsed_seconds: float) -> float | None:
        behavior = point.behavior
        current = self._safe_float(point.present_value, self._safe_float(point.initial_value, 0.0))

        inputs: dict[str, float] = {}
        missing = False
        for key, ref in behavior.response_inputs.items():
            ref_name = str(ref).strip()
            if not ref_name:
                continue
            value = self._resolve_point_value(ref_name)
            if value is None:
                missing = True
                continue
            inputs[str(key)] = value

        policy = (behavior.missing_input_policy or "hold").strip().lower()
        if missing:
            if policy in {"hold", "skip"}:
                return None
            if policy == "fallback":
                next_value = self._safe_float(behavior.fallback_value, current)
            else:
                return None
        else:
            next_value = compute_response(
                kind=behavior.response_kind,
                current=current,
                inputs=inputs,
                params=behavior.response_params,
                dt=elapsed_seconds,
            )

        next_value = self._clamp(next_value, behavior.min_value, behavior.max_value)

        max_rate = max(0.0, self._safe_float(behavior.max_rate_per_sec, 0.0))
        if max_rate > 0.0:
            max_step = max_rate * max(0.0, elapsed_seconds)
            delta = next_value - current
            if delta > max_step:
                next_value = current + max_step
            elif delta < -max_step:
                next_value = current - max_step

        return next_value

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

        # 2) Evaluate point behaviors and response dynamics.
        for device in self._project.devices:
            for point in device.objects:
                if point.object_type in {ObjectType.SCHEDULE, ObjectType.TREND_LOG}:
                    continue

                if point.out_of_service:
                    ref = point.object_ref(device.name)
                    self.registry.set_value(ref, point.present_value)
                    try:
                        numeric = float(point.present_value)
                        self.trends[ref].append((now_real, numeric))
                        snapshot[ref] = numeric
                    except (TypeError, ValueError):
                        pass
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
                        synthetic = schedule_value(point, now_dt)
                        point.present_value = synthetic
                elif point.behavior.mode == BehaviorMode.RESPONSE:
                    evaluated = self._evaluate_response(point, elapsed)
                    if evaluated is not None:
                        point.present_value = evaluated
                else:
                    point.present_value = apply_behavior(point, linked_value, context)

                ref = point.object_ref(device.name)
                self.registry.set_value(ref, point.present_value)
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
                self.registry.set_value(trend_ref, value)
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
