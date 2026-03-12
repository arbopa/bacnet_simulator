from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict

from app.models.device_model import DeviceModel

from .bacnet_objects import (
    BacnetRuntimePoint,
    create_local_object,
    make_device_args,
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
    def __init__(self, bind_ip: str):
        self.bind_ip = bind_ip
        self.devices: Dict[str, BacnetDeviceRuntime] = {}
        self.running = False

    async def start(self, device_models: list[DeviceModel]) -> None:
        from bacpypes3.ipv4.app import Application

        self.devices.clear()
        for model in device_models:
            if not model.enabled:
                continue

            args = make_device_args(
                bind_ip=self.bind_ip,
                udp_port=model.bacnet_port,
                device_name=model.name,
                device_instance=model.device_instance,
                vendor_id=model.vendor_id,
            )
            app = Application.from_args(args)
            runtime = BacnetDeviceRuntime(model=model, application=app)

            for point in model.objects:
                bacnet_obj = create_local_object(point)
                if bacnet_obj is None:
                    continue
                app.add_object(bacnet_obj)
                runtime.points[point.name] = BacnetRuntimePoint(model_point=point, bacnet_object=bacnet_obj)

            self.devices[model.name] = runtime
            logger.info("BACnet device online: %s on %s:%s", model.name, self.bind_ip, model.bacnet_port)

        self.running = True

    async def stop(self) -> None:
        # BACpypes3 applications are cleaned up with loop shutdown.
        self.running = False
        self.devices.clear()

    async def sync_from_model(self) -> None:
        if not self.running:
            return
        for runtime in self.devices.values():
            for point_name, binding in runtime.points.items():
                point = runtime.model.get_object(point_name)
                if point is None:
                    continue
                update_bacnet_object_value(point, binding.bacnet_object)

    async def sync_to_model(self) -> None:
        if not self.running:
            return
        for runtime in self.devices.values():
            for point_name, binding in runtime.points.items():
                point = runtime.model.get_object(point_name)
                if point is None or not point.writable:
                    continue
                try:
                    point.present_value = read_model_value_from_bacnet(point, binding.bacnet_object)
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
