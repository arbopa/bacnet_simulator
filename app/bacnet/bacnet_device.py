from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict

from app.models.device_model import DeviceModel
from app.runtime import PointRegistry

from .bacnet_objects import (
    BacnetRuntimePoint,
    create_local_object,
    read_model_value_from_bacnet,
    update_bacnet_object_value,
)

logger = logging.getLogger(__name__)


@dataclass
class BacnetDeviceRuntime:
    model: DeviceModel
    application: object
    points: Dict[str, BacnetRuntimePoint] = field(default_factory=dict)


class BacnetDeviceServer:
    def __init__(self, bind_ip: str, registry: PointRegistry | None = None):
        self.bind_ip = bind_ip
        self.registry = registry
        self.devices: Dict[str, BacnetDeviceRuntime] = {}
        self.running = False

    async def start(self, device_models: list[DeviceModel]) -> None:
        from bacpypes3.apdu import APCISequence, ConfirmedRequestPDU
        from bacpypes3.app import Application as BaseApplication
        from bacpypes3.errors import UnrecognizedService
        from bacpypes3.ipv4.app import NormalApplication
        from bacpypes3.object import DeviceObject
        from bacpypes3.pdu import IPv4Address
        from bacpypes3.service.object import (
            ReadWritePropertyMultipleServices,
            ReadWritePropertyServices,
        )

        class SimulatorApplication(NormalApplication):
            """Explicitly expose RP/RPM handlers + robust generic confirmed decode."""

            async def do_ReadPropertyRequest(self, apdu):
                logger.debug("RP request %r %r", getattr(apdu, "objectIdentifier", None), getattr(apdu, "propertyIdentifier", None))
                return await ReadWritePropertyServices.do_ReadPropertyRequest(self, apdu)

            async def do_ReadPropertyMultipleRequest(self, apdu):
                logger.debug("RPM request")
                return await ReadWritePropertyMultipleServices.do_ReadPropertyMultipleRequest(self, apdu)

            async def do_ConfirmedRequestPDU(self, apdu):
                logger.info("Generic ConfirmedRequestPDU service=%s from=%s", getattr(apdu, "apduService", None), getattr(apdu, "pduSource", None))
                try:
                    typed_apdu = APCISequence.decode(apdu)
                    logger.info("Decoded confirmed APDU as %s", typed_apdu.__class__.__name__)
                except Exception as err:
                    logger.exception("Failed to decode generic ConfirmedRequestPDU")
                    raise UnrecognizedService(str(err))

                helper_name = "do_" + typed_apdu.__class__.__name__
                helper_fn = getattr(self, helper_name, None)
                logger.info("Dispatch helper=%s exists=%s", helper_name, bool(helper_fn))
                if not helper_fn:
                    raise UnrecognizedService(f"no function {helper_name}")
                return await helper_fn(typed_apdu)

            async def indication(self, apdu):
                logger.info(
                    "Inbound APDU class=%s service=%s src=%s",
                    apdu.__class__.__name__,
                    getattr(apdu, "apduService", None),
                    getattr(apdu, "pduSource", None),
                )
                # Defensive override: if service pipeline leaves APDU generic,
                # force decode and dispatch before base reject path.
                if isinstance(apdu, ConfirmedRequestPDU) and (apdu.__class__.__name__ == "ConfirmedRequestPDU"):
                    try:
                        return await self.do_ConfirmedRequestPDU(apdu)
                    except Exception:
                        logger.exception("Forced generic confirmed dispatch failed")
                        # fall through to base handler for canonical error response
                return await BaseApplication.indication(self, apdu)

        self.devices.clear()
        for model in device_models:
            if not model.enabled:
                continue

            device_object = DeviceObject(
                objectIdentifier=("device", int(model.device_instance)),
                objectName=model.name,
                description=model.description,
                vendorIdentifier=int(model.vendor_id),
                maxApduLengthAccepted=1024,
                segmentationSupported="noSegmentation",
                maxSegmentsAccepted=16,
            )

            local_addr = IPv4Address(f"{self.bind_ip}:{model.bacnet_port}")
            app = SimulatorApplication(device_object, local_addr)
            runtime = BacnetDeviceRuntime(model=model, application=app)

            for point in model.objects:
                bacnet_obj = create_local_object(point)
                if bacnet_obj is None:
                    continue
                app.add_object(bacnet_obj)
                runtime.points[point.name] = BacnetRuntimePoint(model_point=point, bacnet_object=bacnet_obj)

            try:
                device_object.objectList = [obj.objectIdentifier for obj in app.iter_objects()]
            except Exception:
                logger.exception("Failed to populate objectList for %s", model.name)

            logger.info(
                "BACnet device online: %s on %s:%s (RP=%s RPM=%s)",
                model.name,
                self.bind_ip,
                model.bacnet_port,
                hasattr(app, "do_ReadPropertyRequest"),
                hasattr(app, "do_ReadPropertyMultipleRequest"),
            )
            self.devices[model.name] = runtime

        self.running = True

    async def stop(self) -> None:
        for runtime in self.devices.values():
            close_fn = getattr(runtime.application, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    logger.exception("Error closing BACnet application for %s", runtime.model.name)
        self.running = False
        self.devices.clear()

    async def sync_from_model(self) -> None:
        if not self.running:
            return

        if self.registry is None:
            for runtime in self.devices.values():
                for point_name, binding in runtime.points.items():
                    point = runtime.model.get_object(point_name)
                    if point is None:
                        continue
                    update_bacnet_object_value(point, binding.bacnet_object)
            return

        for point_ref in self.registry.claim_dirty_for("bacnet"):
            try:
                device_name, point_name = point_ref.split(".", 1)
            except ValueError:
                self.registry.mark_consumed("bacnet", point_ref)
                continue

            runtime = self.devices.get(device_name)
            if runtime is None:
                self.registry.mark_consumed("bacnet", point_ref)
                continue

            binding = runtime.points.get(point_name)
            if binding is None:
                self.registry.mark_consumed("bacnet", point_ref)
                continue

            runtime_point = self.registry.get(point_ref)
            if runtime_point is None:
                self.registry.mark_consumed("bacnet", point_ref)
                continue

            update_bacnet_object_value(runtime_point.model_point, binding.bacnet_object)
            self.registry.mark_consumed("bacnet", point_ref)

    async def sync_to_model(self) -> None:
        if not self.running:
            return
        for runtime in self.devices.values():
            for point_name, binding in runtime.points.items():
                point = runtime.model.get_object(point_name)
                if point is None or not point.writable:
                    continue
                try:
                    value = read_model_value_from_bacnet(point, binding.bacnet_object)
                    if self.registry is not None:
                        point_ref = f"{runtime.model.name}.{point_name}"
                        if self.registry.set_value(point_ref, value, mark_dirty=False):
                            continue
                    point.present_value = value
                except Exception:
                    logger.exception("Failed syncing writable point %s.%s", runtime.model.name, point_name)

    async def loop_forever(self, tick_event: asyncio.Event, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            await self.sync_from_model()
            await self.sync_to_model()
            try:
                await asyncio.wait_for(tick_event.wait(), timeout=1.0)
                tick_event.clear()
            except asyncio.TimeoutError:
                pass

