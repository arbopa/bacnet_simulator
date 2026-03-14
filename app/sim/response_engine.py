from __future__ import annotations

from typing import Callable, Dict


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct(value) -> float:
    return max(0.0, min(1.0, _as_float(value) / 100.0))


def _first_order(current: float, target: float, tau: float, dt: float) -> float:
    tau = max(0.001, float(tau))
    alpha = min(1.0, max(0.0, dt / tau))
    return current + (target - current) * alpha


def ahu_sat(current: float, inputs: Dict[str, float], params: Dict[str, float], dt: float) -> float:
    base_temp = _as_float(params.get("base_temp", 58.0), 58.0)
    off_temp = _as_float(params.get("off_temp", 70.0), 70.0)
    heat_gain = _as_float(params.get("heat_gain", 25.0), 25.0)
    cool_gain = _as_float(params.get("cool_gain", 30.0), 30.0)
    tau = _as_float(params.get("tau", 20.0), 20.0)

    fan = _as_float(inputs.get("fan_status", 1.0), 1.0)
    if fan < 0.5:
        target = off_temp
    else:
        heating = _pct(inputs.get("heating_valve", 0.0))
        cooling = _pct(inputs.get("cooling_valve", 0.0))
        target = base_temp + heat_gain * heating - cool_gain * cooling

    return _first_order(current, target, tau, dt)


def mixed_air(current: float, inputs: Dict[str, float], params: Dict[str, float], dt: float) -> float:
    oa_temp = _as_float(inputs.get("outdoor_temp", params.get("default_oa_temp", 55.0)), 55.0)
    ra_temp = _as_float(inputs.get("return_temp", params.get("default_ra_temp", 72.0)), 72.0)
    damper = _pct(inputs.get("damper_cmd", 0.0))
    tau = _as_float(params.get("tau", 12.0), 12.0)

    target = oa_temp * damper + ra_temp * (1.0 - damper)
    return _first_order(current, target, tau, dt)


def vav_flow(current: float, inputs: Dict[str, float], params: Dict[str, float], dt: float) -> float:
    damper = _pct(inputs.get("damper_cmd", 0.0))
    min_flow = _as_float(params.get("min_flow", 150.0), 150.0)
    max_flow = _as_float(params.get("max_flow", 900.0), 900.0)
    tau = _as_float(params.get("tau", 8.0), 8.0)

    target = min_flow + damper * (max_flow - min_flow)
    return _first_order(current, target, tau, dt)


def zone_temp(current: float, inputs: Dict[str, float], params: Dict[str, float], dt: float) -> float:
    flow = _as_float(inputs.get("flow", 0.0), 0.0)
    supply_temp = _as_float(inputs.get("supply_temp", params.get("default_supply_temp", 55.0)), 55.0)
    room_load = _as_float(inputs.get("room_load", params.get("default_room_load", 0.2)), 0.2)

    max_flow = max(1.0, _as_float(params.get("max_flow", 900.0), 900.0))
    k_air = _as_float(params.get("k_air", 0.02), 0.02)
    k_load = _as_float(params.get("k_load", 0.03), 0.03)

    airflow_effect = (flow / max_flow) * (supply_temp - current) * k_air
    load_effect = room_load * k_load
    return current + (airflow_effect + load_effect) * dt


def binary_status_delay(current: float, inputs: Dict[str, float], params: Dict[str, float], dt: float) -> float:
    command = 1.0 if _as_float(inputs.get("command", 0.0), 0.0) >= 0.5 else 0.0
    rise_tau = _as_float(params.get("rise_tau", 5.0), 5.0)
    fall_tau = _as_float(params.get("fall_tau", 2.0), 2.0)
    tau = rise_tau if command >= 0.5 else fall_tau
    next_value = _first_order(current, command, tau, dt)
    return 1.0 if next_value >= 0.5 else 0.0


_RESPONSE_FUNCTIONS: Dict[str, Callable[[float, Dict[str, float], Dict[str, float], float], float]] = {
    "ahu_sat": ahu_sat,
    "mixed_air": mixed_air,
    "vav_flow": vav_flow,
    "zone_temp": zone_temp,
    "binary_status_delay": binary_status_delay,
}


def compute_response(kind: str, current: float, inputs: Dict[str, float], params: Dict[str, float], dt: float) -> float:
    fn = _RESPONSE_FUNCTIONS.get((kind or "").strip().lower())
    if fn is None:
        return current
    return fn(current=current, inputs=inputs, params=params, dt=dt)
