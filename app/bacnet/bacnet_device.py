from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict

from app.models.device_model import DeviceModel
from app.models.object_model import ObjectModel
from app.runtime import PointRegistry

from .bacnet_objects import (
    BacnetRuntimePoint,
    create_local_object,
    read_model_value_from_bacnet,
    read_out_of_service_from_bacnet,
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
        self.source_to_bindings: dict[str, list[tuple[str, str]]] = defaultdict(list)
        self.running = False
        self._last_sent_to_bacnet: dict[tuple[str, str], object] = {}

    def _device_bind_ip(self, model: DeviceModel) -> str:
        device_ip = (model.bacnet_ip or "").strip()
        if device_ip and device_ip != "0.0.0.0":
            return device_ip
        return self.bind_ip

    @staticmethod
    def _is_mstp(model: DeviceModel) -> bool:
        return (model.transport or "ip").strip().lower() == "mstp"

    @staticmethod
    def _next_instance(point_type: str, used_by_type: dict[str, set[int]]) -> int:
        used = used_by_type.setdefault(point_type, set())
        if not used:
            used.add(1)
            return 1
        nxt = max(used) + 1
        used.add(nxt)
        return nxt

    @staticmethod
    def _is_fallback_object(point: ObjectModel) -> bool:
        return bool(point.metadata.get("_bacnet_fallback_type"))

    def _add_binding(self, runtime: BacnetDeviceRuntime, key: str, binding: BacnetRuntimePoint) -> None:
        runtime.points[key] = binding
        if binding.source_ref:
            self.source_to_bindings[binding.source_ref].append((runtime.model.name, key))

    def _create_proxy_point(self, child: DeviceModel, source: ObjectModel, used_by_type: dict[str, set[int]]) -> ObjectModel:
        proxy = ObjectModel.from_dict(source.to_dict())
        proxy.name = f"{child.name}_{source.name}"
        proxy.description = f"Proxy of {child.name}.{source.name}"
        proxy.instance = self._next_instance(proxy.object_type.value, used_by_type)
        return proxy

    def _values_equal(self, left: object, right: object) -> bool:
        try:
            return abs(float(left) - float(right)) <= 1e-6
        except (TypeError, ValueError):
            return left == right

    @staticmethod
    def _binding_cache_key(runtime: BacnetDeviceRuntime, binding_key: str) -> tuple[str, str]:
        return (runtime.model.name, binding_key)

    def _update_binding_from_source(self, runtime: BacnetDeviceRuntime, binding_key: str, binding: BacnetRuntimePoint) -> None:
        source = binding.source_point or binding.model_point
        if source is not binding.model_point:
            binding.model_point.present_value = source.present_value
            binding.model_point.out_of_service = bool(source.out_of_service)
        update_bacnet_object_value(source, binding.bacnet_object)
        self._last_sent_to_bacnet[self._binding_cache_key(runtime, binding_key)] = source.present_value

    async def start(self, device_models: list[DeviceModel]) -> None:
        from bacpypes3.ipv4.app import NormalApplication
        from bacpypes3.object import DeviceObject
        from bacpypes3.pdu import IPv4Address

        self.devices.clear()
        self.source_to_bindings.clear()
        self._last_sent_to_bacnet.clear()

        ip_devices = [d for d in device_models if d.enabled and not self._is_mstp(d)]
        mstp_devices = [d for d in device_models if d.enabled and self._is_mstp(d)]
        if not ip_devices:
            raise RuntimeError("No enabled BACnet/IP devices are configured to bind.")

        mstp_by_parent: dict[str, list[DeviceModel]] = defaultdict(list)
        for child in mstp_devices:
            mstp_by_parent[(child.mstp_parent or "").strip()].append(child)

        for model in ip_devices:
            device_object = DeviceObject(
                objectIdentifier=("device", int(model.device_instance)),
                objectName=model.name,
                description=model.description,
                vendorIdentifier=int(model.vendor_id),
                maxApduLengthAccepted=1476,
                segmentationSupported="segmentedBoth",
                maxSegmentsAccepted=64,
            )

            bind_ip = self._device_bind_ip(model)
            local_addr = IPv4Address(f"{bind_ip}:{model.bacnet_port}")
            app = NormalApplication(device_object, local_addr)
            runtime = BacnetDeviceRuntime(model=model, application=app)

            used_by_type: dict[str, set[int]] = defaultdict(set)

            for point in model.objects:
                used_by_type[point.object_type.value].add(int(point.instance))
                bacnet_obj = create_local_object(point)
                if bacnet_obj is None:
                    continue
                if self._is_fallback_object(point):
                    logger.info(
                        "Skipping BACnet fallback object for %s.%s (%s)",
                        model.name,
                        point.name,
                        point.metadata.get("_bacnet_fallback_type"),
                    )
                    continue
                app.add_object(bacnet_obj)
                source_ref = f"{model.name}.{point.name}"
                self._add_binding(
                    runtime,
                    point.name,
                    BacnetRuntimePoint(model_point=point, bacnet_object=bacnet_obj, source_point=point, source_ref=source_ref),
                )

            children = sorted(mstp_by_parent.get(model.name, []), key=lambda d: int(d.mstp_mac or 9999))
            for child in children:
                for child_point in child.objects:
                    proxy_point = self._create_proxy_point(child, child_point, used_by_type)
                    bacnet_obj = create_local_object(proxy_point)
                    if bacnet_obj is None:
                        continue
                    if self._is_fallback_object(proxy_point):
                        logger.info(
                            "Skipping proxy fallback object for %s.%s (%s)",
                            child.name,
                            child_point.name,
                            proxy_point.metadata.get("_bacnet_fallback_type"),
                        )
                        continue
                    app.add_object(bacnet_obj)
                    binding_key = proxy_point.name
                    source_ref = f"{child.name}.{child_point.name}"
                    self._add_binding(
                        runtime,
                        binding_key,
                        BacnetRuntimePoint(
                            model_point=proxy_point,
                            bacnet_object=bacnet_obj,
                            source_point=child_point,
                            source_ref=source_ref,
                        ),
                    )

            try:
                device_object.objectList = [obj.objectIdentifier for obj in app.iter_objects()]
            except Exception:
                logger.exception("Failed to populate objectList for %s", model.name)

            logger.info(
                "BACnet device online: %s on %s:%s (objects=%s)",
                model.name,
                bind_ip,
                model.bacnet_port,
                len(runtime.points),
            )
            self.devices[model.name] = runtime

        for model in mstp_devices:
            logger.info(
                "MS/TP modeled device %s proxied under parent %s (mac=%s)",
                model.name,
                model.mstp_parent,
                model.mstp_mac,
            )

        self.running = True

    def active_bind_endpoints(self) -> list[str]:
        endpoints: list[str] = []
        for runtime in self.devices.values():
            if self._is_mstp(runtime.model):
                continue
            bind_ip = self._device_bind_ip(runtime.model)
            endpoints.append(f"{bind_ip}:{runtime.model.bacnet_port}")
        return sorted(set(endpoints))

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
        self.source_to_bindings.clear()
        self._last_sent_to_bacnet.clear()

    async def sync_from_model(self) -> None:
        if not self.running:
            return

        if self.registry is None:
            for runtime in self.devices.values():
                for binding_key, binding in runtime.points.items():
                    self._update_binding_from_source(runtime, binding_key, binding)
            return

        for point_ref in self.registry.claim_dirty_for("bacnet"):
            mappings = self.source_to_bindings.get(point_ref, [])
            if not mappings:
                self.registry.mark_consumed("bacnet", point_ref)
                continue

            for runtime_name, binding_key in mappings:
                runtime = self.devices.get(runtime_name)
                if runtime is None:
                    continue
                binding = runtime.points.get(binding_key)
                if binding is None:
                    continue
                self._update_binding_from_source(runtime, binding_key, binding)

            self.registry.mark_consumed("bacnet", point_ref)

    async def sync_to_model(self) -> None:
        if not self.running:
            return

        for runtime in self.devices.values():
            for binding_key, binding in runtime.points.items():
                source = binding.source_point or binding.model_point
                if source is None:
                    continue
                try:
                    cache_key = self._binding_cache_key(runtime, binding_key)
                    oos_value = read_out_of_service_from_bacnet(binding.model_point, binding.bacnet_object)
                    oos_changed = bool(source.out_of_service) != bool(oos_value)
                    if oos_changed:
                        source.out_of_service = bool(oos_value)
                        if binding.model_point is not source:
                            binding.model_point.out_of_service = bool(oos_value)

                    value_changed = False
                    if source.writable:
                        value = read_model_value_from_bacnet(binding.model_point, binding.bacnet_object)
                        last_sent = self._last_sent_to_bacnet.get(cache_key)
                        if last_sent is None or not self._values_equal(value, last_sent):
                            source.present_value = value
                            if binding.model_point is not source:
                                binding.model_point.present_value = value
                            self._last_sent_to_bacnet[cache_key] = value
                            value_changed = True

                    if self.registry is not None and binding.source_ref:
                        if value_changed:
                            self.registry.set_value(binding.source_ref, source.present_value, mark_dirty=False)
                        elif oos_changed:
                            self.registry.mark_dirty(binding.source_ref)
                except Exception:
                    logger.exception("Failed syncing writable point %s", binding.source_ref or binding.model_point.name)

    async def loop_forever(self, tick_event: asyncio.Event, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            await self.sync_from_model()
            await self.sync_to_model()
            try:
                await asyncio.wait_for(tick_event.wait(), timeout=1.0)
                tick_event.clear()
            except asyncio.TimeoutError:
                pass

