from __future__ import annotations

from app.models.object_model import ObjectType
from app.models.project_model import ProjectModel


def validate_project(project: ProjectModel) -> list[str]:
    errors: list[str] = []
    device_instances = set()

    for device in project.devices:
        if device.device_instance in device_instances:
            errors.append(f"Duplicate device instance: {device.device_instance}")
        device_instances.add(device.device_instance)

        point_names = set()
        point_instances = set()
        for obj in device.objects:
            if obj.name in point_names:
                errors.append(f"Duplicate point name on {device.name}: {obj.name}")
            point_names.add(obj.name)

            if obj.instance in point_instances:
                errors.append(f"Duplicate object instance on {device.name}: {obj.instance}")
            point_instances.add(obj.instance)

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

    return errors
