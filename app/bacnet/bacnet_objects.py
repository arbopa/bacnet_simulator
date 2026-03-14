from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from app.models.object_model import ObjectModel, ObjectType


@dataclass
class BacnetRuntimePoint:
    model_point: ObjectModel
    bacnet_object: Any
    source_point: ObjectModel | None = None
    source_ref: str = ""


def make_device_args(bind_ip: str, udp_port: int, device_name: str, device_instance: int, vendor_id: int):
    return SimpleNamespace(
        name=device_name,
        instance=int(device_instance),
        vendoridentifier=int(vendor_id),
        address=f"{bind_ip}:{udp_port}",
        network=0,
        foreign=None,
        bbmd=None,
        ttl=30,
    )


def _create_special_object(point: ObjectModel):
    from bacpypes3.local.object import Object as LocalObject
    from bacpypes3.object import ScheduleObject, TrendLogObject
    from bacpypes3.primitivedata import CharacterString

    if point.object_type == ObjectType.SCHEDULE:
        class LocalScheduleObject(LocalObject, ScheduleObject):
            pass

        return LocalScheduleObject(
            objectIdentifier=("schedule", point.instance),
            objectName=CharacterString(point.name),
            description=CharacterString(point.description),
            presentValue=float(point.present_value),
            outOfService=point.out_of_service,
        )

    if point.object_type == ObjectType.TREND_LOG:
        class LocalTrendLogObject(LocalObject, TrendLogObject):
            pass

        return LocalTrendLogObject(
            objectIdentifier=("trendLog", point.instance),
            objectName=CharacterString(point.name),
            description=CharacterString(point.description),
            outOfService=point.out_of_service,
        )

    return None


def _fallback_analog_value_instance(point: ObjectModel) -> int:
    # Keep fallback AV instances in a high range to avoid collisions with normal AVs.
    if point.object_type == ObjectType.SCHEDULE:
        base = 3_000_000
    else:
        base = 3_500_000
    value = base + (int(point.instance) % 500_000)
    return min(4_194_302, value)


def create_local_object(point: ObjectModel):
    from bacpypes3.local.analog import AnalogInputObject, AnalogOutputObject, AnalogValueObject
    from bacpypes3.local.binary import BinaryInputObject, BinaryOutputObject, BinaryValueObject
    from bacpypes3.local.multistate import MultiStateValueObject
    from bacpypes3.primitivedata import CharacterString, Real, Unsigned

    if point.object_type in {ObjectType.SCHEDULE, ObjectType.TREND_LOG}:
        try:
            special = _create_special_object(point)
            if special is not None:
                return special
        except Exception:
            fallback_instance = _fallback_analog_value_instance(point)
            fallback = AnalogValueObject(
                objectIdentifier=("analogValue", fallback_instance),
                objectName=CharacterString(f"{point.name}_fallback"),
                description=CharacterString(f"Fallback for {point.object_type.value}"),
                presentValue=Real(float(point.present_value)),
                outOfService=point.out_of_service,
            )
            point.metadata["_bacnet_fallback_type"] = point.object_type.value
            point.metadata["_bacnet_fallback_instance"] = fallback_instance
            return fallback

    kwargs = {
        "objectIdentifier": (point.object_type.value, point.instance),
        "objectName": CharacterString(point.name),
        "description": CharacterString(point.description),
        "outOfService": point.out_of_service,
    }

    if point.object_type in {
        ObjectType.ANALOG_INPUT,
        ObjectType.ANALOG_OUTPUT,
        ObjectType.ANALOG_VALUE,
    }:
        kwargs["presentValue"] = Real(float(point.present_value))

    if point.object_type in {
        ObjectType.BINARY_INPUT,
        ObjectType.BINARY_OUTPUT,
        ObjectType.BINARY_VALUE,
    }:
        kwargs["presentValue"] = "active" if bool(point.present_value) else "inactive"

    if point.object_type == ObjectType.MULTI_STATE_VALUE:
        kwargs["presentValue"] = Unsigned(int(point.present_value))
        kwargs["numberOfStates"] = Unsigned(10)

    if point.object_type == ObjectType.ANALOG_INPUT:
        return AnalogInputObject(**kwargs)
    if point.object_type == ObjectType.ANALOG_OUTPUT:
        return AnalogOutputObject(**kwargs)
    if point.object_type == ObjectType.ANALOG_VALUE:
        return AnalogValueObject(**kwargs)
    if point.object_type == ObjectType.BINARY_INPUT:
        return BinaryInputObject(**kwargs)
    if point.object_type == ObjectType.BINARY_OUTPUT:
        return BinaryOutputObject(**kwargs)
    if point.object_type == ObjectType.BINARY_VALUE:
        return BinaryValueObject(**kwargs)
    if point.object_type == ObjectType.MULTI_STATE_VALUE:
        return MultiStateValueObject(**kwargs)
    return None


def update_bacnet_object_value(point: ObjectModel, obj: Any) -> None:
    if hasattr(obj, "outOfService"):
        obj.outOfService = bool(point.out_of_service)

    if point.object_type in {
        ObjectType.BINARY_INPUT,
        ObjectType.BINARY_OUTPUT,
        ObjectType.BINARY_VALUE,
    }:
        obj.presentValue = "active" if bool(point.present_value) else "inactive"
        return

    if point.object_type == ObjectType.MULTI_STATE_VALUE:
        obj.presentValue = int(point.present_value)
        return

    if point.object_type in {ObjectType.SCHEDULE, ObjectType.TREND_LOG}:
        if hasattr(obj, "presentValue"):
            obj.presentValue = float(point.present_value)
        return

    obj.presentValue = float(point.present_value)


def read_model_value_from_bacnet(point: ObjectModel, obj: Any):
    raw = getattr(obj, "presentValue", point.present_value)
    if point.object_type in {
        ObjectType.BINARY_INPUT,
        ObjectType.BINARY_OUTPUT,
        ObjectType.BINARY_VALUE,
    }:
        if str(raw).lower() in {"active", "1", "true"}:
            return 1
        return 0
    if point.object_type == ObjectType.MULTI_STATE_VALUE:
        return int(raw)
    return float(raw)


def read_out_of_service_from_bacnet(point: ObjectModel, obj: Any) -> bool:
    return bool(getattr(obj, "outOfService", point.out_of_service))