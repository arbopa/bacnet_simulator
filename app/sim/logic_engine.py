from __future__ import annotations

import operator
import time
from dataclasses import dataclass, field
from typing import Dict

from app.models.project_model import LogicRule, ProjectModel


OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}


@dataclass
class LogicEngine:
    trigger_start: Dict[str, float] = field(default_factory=dict)

    def evaluate(self, project: ProjectModel) -> None:
        now = time.monotonic()
        for rule in project.logic_rules:
            self._apply_rule(project, rule, now)

    def _apply_rule(self, project: ProjectModel, rule: LogicRule, now: float) -> None:
        if not rule.enabled:
            return

        lhs_point = project.get_point_by_ref(rule.lhs_ref)
        action_point = project.get_point_by_ref(rule.action_ref)
        if lhs_point is None or action_point is None:
            return

        op = OPS.get(rule.operator)
        if op is None:
            return

        condition_met = op(lhs_point.present_value, rule.rhs_value)

        if condition_met:
            if rule.delay_seconds > 0:
                start = self.trigger_start.setdefault(rule.name, now)
                if now - start < rule.delay_seconds:
                    return
            action_point.present_value = rule.action_value
            return

        self.trigger_start.pop(rule.name, None)
        if rule.else_value is not None:
            action_point.present_value = rule.else_value
