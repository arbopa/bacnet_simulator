from __future__ import annotations

from typing import Dict, List, Tuple

from .device_model import DeviceModel
from .object_model import BehaviorConfig, BehaviorMode, ObjectModel, ObjectType, ScheduleConfig


def _obj(
    instance: int,
    name: str,
    object_type: ObjectType,
    units: str,
    value,
    writable: bool,
    mode: BehaviorMode = BehaviorMode.MANUAL,
) -> ObjectModel:
    return ObjectModel(
        instance=instance,
        name=name,
        object_type=object_type,
        units=units,
        present_value=value,
        initial_value=value,
        writable=writable,
        relinquish_default=value,
        behavior=BehaviorConfig(mode=mode),
    )


def _set_response(
    point: ObjectModel,
    *,
    kind: str,
    inputs: Dict[str, str],
    params: Dict[str, float],
    min_value: float,
    max_value: float,
    max_rate_per_sec: float = 0.0,
    missing_policy: str = "hold",
    fallback_value: float = 0.0,
) -> None:
    point.behavior.mode = BehaviorMode.RESPONSE
    point.behavior.response_kind = kind
    point.behavior.response_inputs = dict(inputs)
    point.behavior.response_params = dict(params)
    point.behavior.min_value = float(min_value)
    point.behavior.max_value = float(max_value)
    point.behavior.max_rate_per_sec = float(max_rate_per_sec)
    point.behavior.missing_input_policy = missing_policy
    point.behavior.fallback_value = float(fallback_value)


def _schedule_obj(instance: int, name: str, occupied: float = 1.0, unoccupied: float = 0.0) -> ObjectModel:
    return ObjectModel(
        instance=instance,
        name=name,
        object_type=ObjectType.SCHEDULE,
        units="",
        present_value=occupied,
        initial_value=occupied,
        writable=True,
        behavior=BehaviorConfig(mode=BehaviorMode.SCHEDULE),
        schedule=ScheduleConfig(occupied_value=occupied, unoccupied_value=unoccupied),
    )


def _trend_obj(instance: int, name: str, source_ref: str) -> ObjectModel:
    obj = ObjectModel(
        instance=instance,
        name=name,
        object_type=ObjectType.TREND_LOG,
        units="",
        present_value=0.0,
        initial_value=0.0,
        writable=False,
        behavior=BehaviorConfig(mode=BehaviorMode.LOGIC),
    )
    obj.metadata["source_ref"] = source_ref
    return obj


def ahu_template(name: str, device_instance: int, port: int, ip: str = "0.0.0.0") -> DeviceModel:
    points = [
        _obj(1, "OutdoorAirTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 55.0, False, BehaviorMode.SINE),
        _obj(2, "ReturnAirTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 72.0, False, BehaviorMode.SINE),
        _obj(3, "MixedAirTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 65.0, False, BehaviorMode.RESPONSE),
        _obj(4, "SupplyAirTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 58.0, False, BehaviorMode.RESPONSE),
        _obj(5, "SupplyFanCmd", ObjectType.BINARY_OUTPUT, "", 0, True, BehaviorMode.MANUAL),
        _obj(6, "SupplyFanStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.RESPONSE),
        _obj(7, "HeatingValveCmd", ObjectType.ANALOG_OUTPUT, "percent", 0.0, True, BehaviorMode.MANUAL),
        _obj(8, "CoolingValveCmd", ObjectType.ANALOG_OUTPUT, "percent", 20.0, True, BehaviorMode.MANUAL),
        _obj(9, "DamperCmd", ObjectType.ANALOG_OUTPUT, "percent", 30.0, True, BehaviorMode.MANUAL),
        _obj(10, "DamperPos", ObjectType.ANALOG_INPUT, "percent", 30.0, False, BehaviorMode.LINKED),
        _obj(11, "Occupied", ObjectType.BINARY_VALUE, "", 1, True, BehaviorMode.SCHEDULE),
        _obj(12, "SupplyAirSetpoint", ObjectType.ANALOG_VALUE, "degreesFahrenheit", 55.0, True, BehaviorMode.MANUAL),
        _schedule_obj(13, "OccSchedule", 1.0, 0.0),
        _trend_obj(14, "SATTrend", f"{name}.SupplyAirTemp"),
        _obj(15, "DuctStaticPressure", ObjectType.ANALOG_INPUT, "inchesOfWater", 1.5, False, BehaviorMode.RESPONSE),
        _obj(16, "DuctStaticPressureSetpoint", ObjectType.ANALOG_VALUE, "inchesOfWater", 2.0, True, BehaviorMode.MANUAL),
        _obj(17, "SupplyAirflow", ObjectType.ANALOG_INPUT, "cubicFeetPerMinute", 0.0, False, BehaviorMode.RESPONSE),
        _obj(18, "ReturnAirflow", ObjectType.ANALOG_INPUT, "cubicFeetPerMinute", 0.0, False, BehaviorMode.RESPONSE),
        _obj(19, "HeatingValvePos", ObjectType.ANALOG_INPUT, "percent", 0.0, False, BehaviorMode.LINKED),
        _obj(20, "CoolingValvePos", ObjectType.ANALOG_INPUT, "percent", 20.0, False, BehaviorMode.LINKED),
        _obj(21, "FreezeStat", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.RESPONSE),
        _obj(22, "FilterDifferentialPressure", ObjectType.ANALOG_INPUT, "inchesOfWater", 0.4, False, BehaviorMode.RESPONSE),
        _trend_obj(23, "SupplyAirflowTrend", f"{name}.SupplyAirflow"),
    ]

    _set_response(
        points[2],
        kind="mixed_air",
        inputs={
            "outdoor_temp": f"{name}.OutdoorAirTemp",
            "return_temp": f"{name}.ReturnAirTemp",
            "damper_cmd": f"{name}.DamperCmd",
        },
        params={"tau": 12.0},
        min_value=40.0,
        max_value=95.0,
        max_rate_per_sec=5.0,
    )
    _set_response(
        points[3],
        kind="ahu_sat",
        inputs={
            "heating_valve": f"{name}.HeatingValveCmd",
            "cooling_valve": f"{name}.CoolingValveCmd",
            "fan_status": f"{name}.SupplyFanStatus",
        },
        params={"base_temp": 58.0, "off_temp": 72.0, "heat_gain": 25.0, "cool_gain": 30.0, "tau": 20.0},
        min_value=45.0,
        max_value=95.0,
        max_rate_per_sec=4.0,
    )
    _set_response(
        points[5],
        kind="binary_status_delay",
        inputs={"command": f"{name}.SupplyFanCmd"},
        params={"rise_tau": 5.0, "fall_tau": 2.0},
        min_value=0.0,
        max_value=1.0,
        max_rate_per_sec=0.0,
    )
    _set_response(
        points[14],
        kind="duct_static_pressure",
        inputs={
            "fan_status": f"{name}.SupplyFanStatus",
            "airflow": f"{name}.SupplyAirflow",
            "setpoint": f"{name}.DuctStaticPressureSetpoint",
        },
        params={"design_flow": 20000.0, "off_pressure": 0.05, "tau": 10.0},
        min_value=0.0,
        max_value=4.0,
        max_rate_per_sec=0.8,
    )
    _set_response(
        points[16],
        kind="airflow_from_fan",
        inputs={"fan_status": f"{name}.SupplyFanStatus"},
        params={"design_flow": 20000.0, "min_flow": 0.0, "tau": 14.0},
        min_value=0.0,
        max_value=24000.0,
        max_rate_per_sec=3500.0,
    )
    _set_response(
        points[17],
        kind="scaled_input",
        inputs={"source": f"{name}.SupplyAirflow"},
        params={"gain": 0.85, "bias": 0.0, "tau": 18.0},
        min_value=0.0,
        max_value=22000.0,
        max_rate_per_sec=3000.0,
    )
    _set_response(
        points[20],
        kind="binary_low_trip",
        inputs={"source": f"{name}.MixedAirTemp"},
        params={"trip": 38.0, "reset": 42.0},
        min_value=0.0,
        max_value=1.0,
        max_rate_per_sec=0.0,
    )
    _set_response(
        points[21],
        kind="scaled_input",
        inputs={"source": f"{name}.SupplyAirflow"},
        params={"gain": 0.00008, "bias": 0.2, "tau": 25.0},
        min_value=0.1,
        max_value=3.0,
        max_rate_per_sec=0.2,
    )

    points[9].behavior.linked_point_ref = f"{name}.DamperCmd"
    points[10].schedule.schedule_ref = f"{name}.OccSchedule"
    points[18].behavior.linked_point_ref = f"{name}.HeatingValveCmd"
    points[19].behavior.linked_point_ref = f"{name}.CoolingValveCmd"

    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="AHU Controller",
        bacnet_ip=ip,
        bacnet_port=port,
        objects=points,
    )


def vav_template(name: str, device_instance: int, port: int, ip: str = "0.0.0.0") -> DeviceModel:
    points = [
        _obj(1, "ZoneTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 73.0, False, BehaviorMode.RESPONSE),
        _obj(2, "ZoneSetpoint", ObjectType.ANALOG_VALUE, "degreesFahrenheit", 72.0, True, BehaviorMode.MANUAL),
        _obj(3, "DamperCmd", ObjectType.ANALOG_OUTPUT, "percent", 25.0, True, BehaviorMode.LOGIC),
        _obj(4, "DamperPos", ObjectType.ANALOG_INPUT, "percent", 25.0, False, BehaviorMode.LINKED),
        _obj(5, "Flow", ObjectType.ANALOG_INPUT, "cubicFeetPerMinute", 450.0, False, BehaviorMode.RESPONSE),
        _obj(6, "ReheatCmd", ObjectType.ANALOG_OUTPUT, "percent", 0.0, True, BehaviorMode.LOGIC),
        _obj(7, "Occupied", ObjectType.BINARY_VALUE, "", 1, True, BehaviorMode.SCHEDULE),
        _schedule_obj(8, "OccSchedule", 1.0, 0.0),
        _trend_obj(9, "ZoneTempTrend", f"{name}.ZoneTemp"),
    ]

    _set_response(
        points[4],
        kind="vav_flow",
        inputs={"damper_cmd": f"{name}.DamperCmd"},
        params={"min_flow": 150.0, "max_flow": 900.0, "tau": 8.0},
        min_value=0.0,
        max_value=1200.0,
        max_rate_per_sec=300.0,
    )
    _set_response(
        points[0],
        kind="zone_temp",
        inputs={"flow": f"{name}.Flow"},
        params={"default_supply_temp": 55.0, "default_room_load": 0.2, "max_flow": 900.0, "k_air": 0.02, "k_load": 0.03},
        min_value=55.0,
        max_value=90.0,
        max_rate_per_sec=0.5,
    )

    points[3].behavior.linked_point_ref = f"{name}.DamperCmd"
    points[6].schedule.schedule_ref = f"{name}.OccSchedule"
    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="VAV Controller",
        bacnet_ip=ip,
        bacnet_port=port,
        objects=points,
    )


def boiler_template(name: str, device_instance: int, port: int, ip: str = "0.0.0.0") -> DeviceModel:
    points = [
        _obj(1, "Enable", ObjectType.BINARY_VALUE, "", 0, True, BehaviorMode.MANUAL),
        _obj(2, "PumpCmd", ObjectType.BINARY_OUTPUT, "", 0, True, BehaviorMode.LOGIC),
        _obj(3, "PumpStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.LINKED),
        _obj(4, "WaterTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 120.0, False, BehaviorMode.RESPONSE),
        _obj(5, "WaterSetpoint", ObjectType.ANALOG_VALUE, "degreesFahrenheit", 140.0, True, BehaviorMode.MANUAL),
        _obj(6, "Alarm", ObjectType.BINARY_VALUE, "", 0, True, BehaviorMode.LOGIC),
        _trend_obj(7, "WaterTempTrend", f"{name}.WaterTemp"),
        _obj(8, "RunStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.RESPONSE),
        _obj(9, "ReturnWaterTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 115.0, False, BehaviorMode.RESPONSE),
        _obj(10, "GasValveCmd", ObjectType.ANALOG_OUTPUT, "percent", 40.0, True, BehaviorMode.MANUAL),
        _obj(11, "GasValvePos", ObjectType.ANALOG_INPUT, "percent", 40.0, False, BehaviorMode.LINKED),
        _obj(12, "CondensateValveCmd", ObjectType.BINARY_OUTPUT, "", 1, True, BehaviorMode.MANUAL),
        _obj(13, "CondensateValveStatus", ObjectType.BINARY_INPUT, "", 1, False, BehaviorMode.LINKED),
        _obj(14, "HeaderPressure", ObjectType.ANALOG_INPUT, "poundsForcePerSquareInch", 6.0, False, BehaviorMode.RESPONSE),
        _trend_obj(15, "ReturnWaterTempTrend", f"{name}.ReturnWaterTemp"),
    ]

    _set_response(
        points[3],
        kind="boiler_water_temp",
        inputs={
            "run_status": f"{name}.RunStatus",
            "setpoint": f"{name}.WaterSetpoint",
            "return_temp": f"{name}.ReturnWaterTemp",
            "gas_valve_cmd": f"{name}.GasValveCmd",
        },
        params={"off_temp": 110.0, "tau": 90.0},
        min_value=80.0,
        max_value=210.0,
        max_rate_per_sec=2.0,
    )
    _set_response(
        points[7],
        kind="binary_status_delay",
        inputs={"command": f"{name}.Enable"},
        params={"rise_tau": 8.0, "fall_tau": 4.0},
        min_value=0.0,
        max_value=1.0,
        max_rate_per_sec=0.0,
    )
    _set_response(
        points[8],
        kind="scaled_input",
        inputs={"source": f"{name}.WaterTemp"},
        params={"gain": 1.0, "bias": -18.0, "tau": 40.0},
        min_value=70.0,
        max_value=200.0,
        max_rate_per_sec=1.5,
    )
    _set_response(
        points[13],
        kind="scaled_input",
        inputs={"source": f"{name}.PumpStatus"},
        params={"gain": 4.0, "bias": 2.0, "tau": 20.0},
        min_value=0.0,
        max_value=12.0,
        max_rate_per_sec=0.8,
    )

    points[2].behavior.linked_point_ref = f"{name}.PumpCmd"
    points[10].behavior.linked_point_ref = f"{name}.GasValveCmd"
    points[12].behavior.linked_point_ref = f"{name}.CondensateValveCmd"

    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="Boiler Controller",
        bacnet_ip=ip,
        bacnet_port=port,
        objects=points,
    )


def chiller_template(name: str, device_instance: int, port: int, ip: str = "0.0.0.0") -> DeviceModel:
    points = [
        _obj(1, "Enable", ObjectType.BINARY_VALUE, "", 0, True, BehaviorMode.MANUAL),
        _obj(2, "RunStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.RESPONSE),
        _obj(3, "LeavingWaterTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 48.0, False, BehaviorMode.RESPONSE),
        _obj(4, "EnteringWaterTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 56.0, False, BehaviorMode.RESPONSE),
        _obj(5, "Setpoint", ObjectType.ANALOG_VALUE, "degreesFahrenheit", 44.0, True, BehaviorMode.MANUAL),
        _obj(6, "Alarm", ObjectType.BINARY_VALUE, "", 0, True, BehaviorMode.LOGIC),
        _trend_obj(7, "LWTTrend", f"{name}.LeavingWaterTemp"),
        _obj(8, "CondenserWaterValveCmd", ObjectType.ANALOG_OUTPUT, "percent", 35.0, True, BehaviorMode.MANUAL),
        _obj(9, "CondenserWaterValvePos", ObjectType.ANALOG_INPUT, "percent", 35.0, False, BehaviorMode.LINKED),
        _obj(10, "ChilledWaterValveCmd", ObjectType.ANALOG_OUTPUT, "percent", 80.0, True, BehaviorMode.MANUAL),
        _obj(11, "ChilledWaterValvePos", ObjectType.ANALOG_INPUT, "percent", 80.0, False, BehaviorMode.LINKED),
        _obj(12, "EvapFlow", ObjectType.ANALOG_INPUT, "cubicFeetPerMinute", 0.0, False, BehaviorMode.RESPONSE),
        _obj(13, "CondFlow", ObjectType.ANALOG_INPUT, "cubicFeetPerMinute", 0.0, False, BehaviorMode.RESPONSE),
        _obj(14, "CondensateDrainValveCmd", ObjectType.BINARY_OUTPUT, "", 1, True, BehaviorMode.MANUAL),
        _obj(15, "CondensateDrainValveStatus", ObjectType.BINARY_INPUT, "", 1, False, BehaviorMode.LINKED),
        _trend_obj(16, "CondFlowTrend", f"{name}.CondFlow"),
    ]

    _set_response(
        points[1],
        kind="binary_status_delay",
        inputs={"command": f"{name}.Enable"},
        params={"rise_tau": 12.0, "fall_tau": 6.0},
        min_value=0.0,
        max_value=1.0,
        max_rate_per_sec=0.0,
    )
    _set_response(
        points[2],
        kind="chiller_lwt",
        inputs={
            "run_status": f"{name}.RunStatus",
            "setpoint": f"{name}.Setpoint",
            "entering_temp": f"{name}.EnteringWaterTemp",
            "chw_valve_cmd": f"{name}.ChilledWaterValveCmd",
        },
        params={"off_temp": 62.0, "tau": 75.0},
        min_value=36.0,
        max_value=70.0,
        max_rate_per_sec=1.0,
    )
    _set_response(
        points[3],
        kind="chiller_ewt",
        inputs={
            "run_status": f"{name}.RunStatus",
            "leaving_temp": f"{name}.LeavingWaterTemp",
            "cond_valve_cmd": f"{name}.CondenserWaterValveCmd",
        },
        params={"off_temp": 66.0, "delta_t": 8.0, "tau": 90.0},
        min_value=40.0,
        max_value=90.0,
        max_rate_per_sec=1.0,
    )
    _set_response(
        points[11],
        kind="scaled_input",
        inputs={"source": f"{name}.RunStatus"},
        params={"gain": 1200.0, "bias": 0.0, "tau": 18.0},
        min_value=0.0,
        max_value=1600.0,
        max_rate_per_sec=220.0,
    )
    _set_response(
        points[12],
        kind="scaled_input",
        inputs={"source": f"{name}.RunStatus"},
        params={"gain": 1400.0, "bias": 0.0, "tau": 18.0},
        min_value=0.0,
        max_value=1800.0,
        max_rate_per_sec=240.0,
    )

    points[8].behavior.linked_point_ref = f"{name}.CondenserWaterValveCmd"
    points[10].behavior.linked_point_ref = f"{name}.ChilledWaterValveCmd"
    points[14].behavior.linked_point_ref = f"{name}.CondensateDrainValveCmd"

    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="Chiller Controller",
        bacnet_ip=ip,
        bacnet_port=port,
        objects=points,
    )


def pump_template(name: str, device_instance: int, port: int, ip: str = "0.0.0.0") -> DeviceModel:
    points = [
        _obj(1, "Enable", ObjectType.BINARY_VALUE, "", 0, True),
        _obj(2, "LeadPumpCmd", ObjectType.BINARY_OUTPUT, "", 0, True),
        _obj(3, "LeadPumpStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.LINKED),
        _obj(4, "DifferentialPressure", ObjectType.ANALOG_INPUT, "poundsForcePerSquareInch", 12.0, False, BehaviorMode.RESPONSE),
        _trend_obj(5, "DPTrend", f"{name}.DifferentialPressure"),
        _obj(6, "CWPumpCmd", ObjectType.BINARY_OUTPUT, "", 0, True),
        _obj(7, "CWPumpStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.LINKED),
        _obj(8, "CWDifferentialPressure", ObjectType.ANALOG_INPUT, "poundsForcePerSquareInch", 10.0, False, BehaviorMode.RESPONSE),
        _obj(9, "HWPumpCmd", ObjectType.BINARY_OUTPUT, "", 0, True),
        _obj(10, "HWPumpStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.LINKED),
        _obj(11, "HWDifferentialPressure", ObjectType.ANALOG_INPUT, "poundsForcePerSquareInch", 8.0, False, BehaviorMode.RESPONSE),
        _obj(12, "CHWIsolationValveCmd", ObjectType.ANALOG_OUTPUT, "percent", 70.0, True, BehaviorMode.MANUAL),
        _obj(13, "CHWIsolationValvePos", ObjectType.ANALOG_INPUT, "percent", 70.0, False, BehaviorMode.LINKED),
        _obj(14, "CWIsolationValveCmd", ObjectType.ANALOG_OUTPUT, "percent", 70.0, True, BehaviorMode.MANUAL),
        _obj(15, "CWIsolationValvePos", ObjectType.ANALOG_INPUT, "percent", 70.0, False, BehaviorMode.LINKED),
        _obj(16, "HWIsolationValveCmd", ObjectType.ANALOG_OUTPUT, "percent", 70.0, True, BehaviorMode.MANUAL),
        _obj(17, "HWIsolationValvePos", ObjectType.ANALOG_INPUT, "percent", 70.0, False, BehaviorMode.LINKED),
        _obj(18, "HeaderTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 58.0, False, BehaviorMode.SINE),
        _trend_obj(19, "HeaderTempTrend", f"{name}.HeaderTemp"),
    ]

    _set_response(
        points[3],
        kind="differential_pressure",
        inputs={"pump_status": f"{name}.LeadPumpStatus", "valve_cmd": f"{name}.CHWIsolationValveCmd"},
        params={"min_dp": 2.0, "max_dp": 25.0, "tau": 10.0},
        min_value=0.0,
        max_value=30.0,
        max_rate_per_sec=2.0,
    )
    _set_response(
        points[7],
        kind="differential_pressure",
        inputs={"pump_status": f"{name}.CWPumpStatus", "valve_cmd": f"{name}.CWIsolationValveCmd"},
        params={"min_dp": 2.0, "max_dp": 22.0, "tau": 10.0},
        min_value=0.0,
        max_value=28.0,
        max_rate_per_sec=2.0,
    )
    _set_response(
        points[10],
        kind="differential_pressure",
        inputs={"pump_status": f"{name}.HWPumpStatus", "valve_cmd": f"{name}.HWIsolationValveCmd"},
        params={"min_dp": 2.0, "max_dp": 20.0, "tau": 10.0},
        min_value=0.0,
        max_value=25.0,
        max_rate_per_sec=2.0,
    )

    points[2].behavior.linked_point_ref = f"{name}.LeadPumpCmd"
    points[6].behavior.linked_point_ref = f"{name}.CWPumpCmd"
    points[9].behavior.linked_point_ref = f"{name}.HWPumpCmd"
    points[12].behavior.linked_point_ref = f"{name}.CHWIsolationValveCmd"
    points[14].behavior.linked_point_ref = f"{name}.CWIsolationValveCmd"
    points[16].behavior.linked_point_ref = f"{name}.HWIsolationValveCmd"

    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="Pump Panel",
        bacnet_ip=ip,
        bacnet_port=port,
        objects=points,
    )


def generic_controller_template(name: str, device_instance: int, port: int, ip: str = "0.0.0.0") -> DeviceModel:
    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="Generic Field Controller",
        bacnet_ip=ip,
        bacnet_port=port,
        objects=[
            _obj(1, "AI1", ObjectType.ANALOG_INPUT, "noUnits", 0.0, False, BehaviorMode.RANDOM),
            _obj(2, "AO1", ObjectType.ANALOG_OUTPUT, "noUnits", 0.0, True, BehaviorMode.MANUAL),
            _obj(3, "AV1", ObjectType.ANALOG_VALUE, "noUnits", 0.0, True, BehaviorMode.MANUAL),
            _obj(4, "BI1", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.RANDOM),
            _obj(5, "BO1", ObjectType.BINARY_OUTPUT, "", 0, True, BehaviorMode.MANUAL),
            _obj(6, "BV1", ObjectType.BINARY_VALUE, "", 0, True, BehaviorMode.MANUAL),
            _obj(7, "MSV1", ObjectType.MULTI_STATE_VALUE, "", 1, True, BehaviorMode.MANUAL),
            _schedule_obj(8, "GenericSchedule", 1.0, 0.0),
            _trend_obj(9, "AI1Trend", f"{name}.AI1"),
        ],
    )


def template_choices() -> List[Tuple[str, str]]:
    return [
        ("AHU", "ahu"),
        ("VAV", "vav"),
        ("Boiler", "boiler"),
        ("Chiller", "chiller"),
        ("Pump", "pump"),
        ("Generic", "generic"),
    ]


def build_template(
    template_key: str,
    name: str,
    device_instance: int,
    port: int,
    ip: str = "0.0.0.0",
    transport: str = "ip",
    mstp_parent: str = "",
    mstp_mac: int | None = None,
) -> DeviceModel:
    key = template_key.lower()
    if key == "ahu":
        device = ahu_template(name, device_instance, port, ip)
    elif key == "vav":
        device = vav_template(name, device_instance, port, ip)
    elif key == "boiler":
        device = boiler_template(name, device_instance, port, ip)
    elif key == "chiller":
        device = chiller_template(name, device_instance, port, ip)
    elif key == "pump":
        device = pump_template(name, device_instance, port, ip)
    else:
        device = generic_controller_template(name, device_instance, port, ip)

    normalized_transport = (transport or "ip").strip().lower()
    if normalized_transport not in {"ip", "mstp"}:
        normalized_transport = "ip"

    device.transport = normalized_transport
    if normalized_transport == "mstp":
        device.bacnet_ip = ""
        device.mstp_parent = (mstp_parent or "").strip()
        device.mstp_mac = mstp_mac
    else:
        device.bacnet_ip = ip
        device.mstp_parent = ""
        device.mstp_mac = None

    return device