from __future__ import annotations

from app.models.project_model import ProjectModel


def apply_scenario(project: ProjectModel) -> None:
    scenario = project.scenario
    for device in project.devices:
        occupied = device.get_object("Occupied")
        if occupied is not None:
            occupied.present_value = 1 if scenario.occupied else 0

        oat = device.get_object("OutdoorAirTemp")
        if oat is not None:
            oat.present_value = scenario.outdoor_air_temp

        alarm = device.get_object("Alarm")
        if alarm is not None and scenario.alarm_injection:
            alarm.present_value = 1
