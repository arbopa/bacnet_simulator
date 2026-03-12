from __future__ import annotations

from typing import List, Tuple

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


def ahu_template(name: str, device_instance: int, port: int) -> DeviceModel:
    points = [
        _obj(1, "OutdoorAirTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 55.0, False, BehaviorMode.SINE),
        _obj(2, "ReturnAirTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 72.0, False, BehaviorMode.SINE),
        _obj(3, "MixedAirTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 65.0, False, BehaviorMode.LOGIC),
        _obj(4, "SupplyAirTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 58.0, False, BehaviorMode.LOGIC),
        _obj(5, "SupplyFanCmd", ObjectType.BINARY_OUTPUT, "", 0, True, BehaviorMode.MANUAL),
        _obj(6, "SupplyFanStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.LOGIC),
        _obj(7, "HeatingValveCmd", ObjectType.ANALOG_OUTPUT, "percent", 0.0, True, BehaviorMode.MANUAL),
        _obj(8, "CoolingValveCmd", ObjectType.ANALOG_OUTPUT, "percent", 20.0, True, BehaviorMode.MANUAL),
        _obj(9, "DamperCmd", ObjectType.ANALOG_OUTPUT, "percent", 30.0, True, BehaviorMode.MANUAL),
        _obj(10, "DamperPos", ObjectType.ANALOG_INPUT, "percent", 30.0, False, BehaviorMode.LINKED),
        _obj(11, "Occupied", ObjectType.BINARY_VALUE, "", 1, True, BehaviorMode.SCHEDULE),
        _obj(12, "SupplyAirSetpoint", ObjectType.ANALOG_VALUE, "degreesFahrenheit", 55.0, True, BehaviorMode.MANUAL),
        _schedule_obj(13, "OccSchedule", 1.0, 0.0),
        _trend_obj(14, "SATTrend", f"{name}.SupplyAirTemp"),
    ]
    points[9].behavior.linked_point_ref = f"{name}.DamperCmd"
    points[10].schedule.schedule_ref = f"{name}.OccSchedule"
    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="AHU Controller",
        bacnet_port=port,
        objects=points,
    )


def vav_template(name: str, device_instance: int, port: int) -> DeviceModel:
    points = [
        _obj(1, "ZoneTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 73.0, False, BehaviorMode.LOGIC),
        _obj(2, "ZoneSetpoint", ObjectType.ANALOG_VALUE, "degreesFahrenheit", 72.0, True, BehaviorMode.MANUAL),
        _obj(3, "DamperCmd", ObjectType.ANALOG_OUTPUT, "percent", 25.0, True, BehaviorMode.LOGIC),
        _obj(4, "DamperPos", ObjectType.ANALOG_INPUT, "percent", 25.0, False, BehaviorMode.LINKED),
        _obj(5, "Flow", ObjectType.ANALOG_INPUT, "cubicFeetPerMinute", 450.0, False, BehaviorMode.LOGIC),
        _obj(6, "ReheatCmd", ObjectType.ANALOG_OUTPUT, "percent", 0.0, True, BehaviorMode.LOGIC),
        _obj(7, "Occupied", ObjectType.BINARY_VALUE, "", 1, True, BehaviorMode.SCHEDULE),
        _schedule_obj(8, "OccSchedule", 1.0, 0.0),
        _trend_obj(9, "ZoneTempTrend", f"{name}.ZoneTemp"),
    ]
    points[3].behavior.linked_point_ref = f"{name}.DamperCmd"
    points[6].schedule.schedule_ref = f"{name}.OccSchedule"
    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="VAV Controller",
        bacnet_port=port,
        objects=points,
    )


def boiler_template(name: str, device_instance: int, port: int) -> DeviceModel:
    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="Boiler Controller",
        bacnet_port=port,
        objects=[
            _obj(1, "Enable", ObjectType.BINARY_VALUE, "", 0, True, BehaviorMode.MANUAL),
            _obj(2, "PumpCmd", ObjectType.BINARY_OUTPUT, "", 0, True, BehaviorMode.LOGIC),
            _obj(3, "PumpStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.LINKED),
            _obj(4, "WaterTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 120.0, False, BehaviorMode.LOGIC),
            _obj(5, "WaterSetpoint", ObjectType.ANALOG_VALUE, "degreesFahrenheit", 140.0, True, BehaviorMode.MANUAL),
            _obj(6, "Alarm", ObjectType.BINARY_VALUE, "", 0, True, BehaviorMode.LOGIC),
            _trend_obj(7, "WaterTempTrend", f"{name}.WaterTemp"),
        ],
    )


def chiller_template(name: str, device_instance: int, port: int) -> DeviceModel:
    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="Chiller Controller",
        bacnet_port=port,
        objects=[
            _obj(1, "Enable", ObjectType.BINARY_VALUE, "", 0, True, BehaviorMode.MANUAL),
            _obj(2, "RunStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.LOGIC),
            _obj(3, "LeavingWaterTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 48.0, False, BehaviorMode.LOGIC),
            _obj(4, "EnteringWaterTemp", ObjectType.ANALOG_INPUT, "degreesFahrenheit", 56.0, False, BehaviorMode.LOGIC),
            _obj(5, "Setpoint", ObjectType.ANALOG_VALUE, "degreesFahrenheit", 44.0, True, BehaviorMode.MANUAL),
            _obj(6, "Alarm", ObjectType.BINARY_VALUE, "", 0, True, BehaviorMode.LOGIC),
            _trend_obj(7, "LWTTrend", f"{name}.LeavingWaterTemp"),
        ],
    )


def pump_template(name: str, device_instance: int, port: int) -> DeviceModel:
    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="Pump Panel",
        bacnet_port=port,
        objects=[
            _obj(1, "Enable", ObjectType.BINARY_VALUE, "", 0, True),
            _obj(2, "LeadPumpCmd", ObjectType.BINARY_OUTPUT, "", 0, True),
            _obj(3, "LeadPumpStatus", ObjectType.BINARY_INPUT, "", 0, False, BehaviorMode.LINKED),
            _obj(4, "DifferentialPressure", ObjectType.ANALOG_INPUT, "poundsForcePerSquareInch", 12.0, False, BehaviorMode.LOGIC),
            _trend_obj(5, "DPTrend", f"{name}.DifferentialPressure"),
        ],
    )


def generic_controller_template(name: str, device_instance: int, port: int) -> DeviceModel:
    return DeviceModel(
        name=name,
        device_instance=device_instance,
        vendor_id=999,
        description="Generic Field Controller",
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


def build_template(template_key: str, name: str, device_instance: int, port: int) -> DeviceModel:
    key = template_key.lower()
    if key == "ahu":
        return ahu_template(name, device_instance, port)
    if key == "vav":
        return vav_template(name, device_instance, port)
    if key == "boiler":
        return boiler_template(name, device_instance, port)
    if key == "chiller":
        return chiller_template(name, device_instance, port)
    if key == "pump":
        return pump_template(name, device_instance, port)
    return generic_controller_template(name, device_instance, port)
