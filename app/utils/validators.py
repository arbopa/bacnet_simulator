from __future__ import annotations

import ipaddress

from app.models.object_model import ObjectType
from app.models.project_model import ProjectModel


_VALID_MISSING_POLICIES = {"hold", "skip", "fallback"}


def validate_project(project: ProjectModel) -> list[str]:
    errors: list[str] = []
    device_instances = set()
    bound_endpoints = set()

    devices_by_name = {device.name: device for device in project.devices}
    mstp_mac_by_parent = set()

    for device in project.devices:
        if device.device_instance in device_instances:
            errors.append(f"Duplicate device instance: {device.device_instance}")
        device_instances.add(device.device_instance)

        transport = (device.transport or "ip").strip().lower()
        if transport not in {"ip", "mstp"}:
            errors.append(f"Invalid transport on {device.name}: {device.transport}")
            transport = "ip"

        if transport == "ip":
            device_ip = (device.bacnet_ip or "").strip()
            if device_ip and device_ip != "0.0.0.0":
                try:
                    ipaddress.ip_address(device_ip)
                except ValueError:
                    errors.append(f"Invalid BACnet IP on {device.name}: {device_ip}")

            bind_ip = device_ip if device_ip and device_ip != "0.0.0.0" else project.bacnet.bind_ip
            endpoint = (bind_ip, device.bacnet_port)
            if endpoint in bound_endpoints:
                errors.append(f"Duplicate BACnet bind target: {bind_ip}:{device.bacnet_port}")
            bound_endpoints.add(endpoint)
        else:
            parent_name = (device.mstp_parent or "").strip()
            if not parent_name:
                errors.append(f"MS/TP device {device.name} is missing parent device name")
            if device.mstp_mac is None:
                errors.append(f"MS/TP device {device.name} is missing MAC address")
            else:
                if not (0 <= int(device.mstp_mac) <= 127):
                    errors.append(f"MS/TP MAC out of range on {device.name}: {device.mstp_mac}")
                key = (parent_name, int(device.mstp_mac))
                if key in mstp_mac_by_parent:
                    errors.append(f"Duplicate MS/TP MAC on parent {parent_name}: {device.mstp_mac}")
                mstp_mac_by_parent.add(key)

        point_names = set()
        point_instances = set()
        for obj in device.objects:
            if obj.name in point_names:
                errors.append(f"Duplicate point name on {device.name}: {obj.name}")
            point_names.add(obj.name)

            if obj.instance in point_instances:
                errors.append(f"Duplicate object instance on {device.name}: {obj.instance}")
            point_instances.add(obj.instance)

    for device in project.devices:
        transport = (device.transport or "ip").strip().lower()
        if transport != "mstp":
            continue

        parent_name = (device.mstp_parent or "").strip()
        if not parent_name:
            continue

        parent = devices_by_name.get(parent_name)
        if parent is None:
            errors.append(f"MS/TP parent not found for {device.name}: {parent_name}")
            continue

        parent_transport = (parent.transport or "ip").strip().lower()
        if parent_transport != "ip":
            errors.append(f"MS/TP parent must be BACnet/IP for {device.name}: {parent_name}")

    refs = set(project.all_point_refs())
    for device in project.devices:
        for obj in device.objects:
            if obj.behavior.linked_point_ref and obj.behavior.linked_point_ref not in refs:
                errors.append(f"Invalid linked point ref on {device.name}.{obj.name}: {obj.behavior.linked_point_ref}")
            if obj.schedule.schedule_ref and obj.schedule.schedule_ref not in refs:
                errors.append(f"Invalid schedule ref on {device.name}.{obj.name}: {obj.schedule.schedule_ref}")
            if obj.object_type == ObjectType.TREND_LOG:
                source_ref = str(obj.metadata.get("source_ref", "")).strip()
                if source_ref and source_ref not in refs:
                    errors.append(f"Invalid trend source ref on {device.name}.{obj.name}: {source_ref}")

            if obj.behavior.mode.value == "response":
                policy = (obj.behavior.missing_input_policy or "hold").strip().lower()
                if policy not in _VALID_MISSING_POLICIES:
                    errors.append(
                        f"Invalid missing_input_policy on {device.name}.{obj.name}: {obj.behavior.missing_input_policy}"
                    )
                for key, ref in obj.behavior.response_inputs.items():
                    ref_name = str(ref).strip()
                    if ref_name and ref_name not in refs:
                        errors.append(f"Invalid response input ref on {device.name}.{obj.name} [{key}]: {ref_name}")

    return errors
