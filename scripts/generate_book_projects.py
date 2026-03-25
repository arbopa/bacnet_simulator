from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.models.device_model import DeviceModel
from app.models.project_model import BacnetSettings, LogicRule, ProjectModel, ScenarioState
from app.models.template_defs import build_template
from app.storage.project_io import save_project
from app.utils.validators import validate_project


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "sample_projects" / "book"


@dataclass
class JaceSpec:
    name: str
    device_id: int
    ip: str


@dataclass
class MstpSpec:
    name: str
    device_id: int
    template: str
    parent: str
    mac: int
    mstp_network: int


PROJECT_SPECS: dict[str, dict] = {
    "P1_JACE1_AHU4VAV_MSTP": {
        "project_name": "Single Floor Office (1 JACE + AHU/VAV trunk)",
        "recommended_package": "bacsim_p1_jace1_ahu4vav_mstp_v1",
        "fault_scenarios": ["normal_day", "fan_fail", "sensor_drift", "stuck_damper", "device_offline"],
        "jaces": [JaceSpec("JACE-9000-A", 1900, "10.77.1.10")],
        "mstp_devices": [
            MstpSpec("AHU-1", 2000, "ahu", "JACE-9000-A", 1, 100),
            MstpSpec("VAV-1", 2001, "vav", "JACE-9000-A", 2, 100),
            MstpSpec("VAV-2", 2002, "vav", "JACE-9000-A", 3, 100),
            MstpSpec("VAV-3", 2003, "vav", "JACE-9000-A", 4, 100),
            MstpSpec("VAV-4", 2004, "vav", "JACE-9000-A", 5, 100),
        ],
    },
    "P2_JACE_PER_FLOOR": {
        "project_name": "Multi-Floor Office (1 JACE per floor)",
        "recommended_package": "bacsim_p2_jace_per_floor_v1",
        "fault_scenarios": [
            "normal_day",
            "fan_fail",
            "sensor_drift",
            "stuck_damper",
            "device_offline",
            "floor_jace_offline",
        ],
        "jaces": [
            JaceSpec("JACE-9000-A", 1900, "10.77.2.10"),
            JaceSpec("JACE-9000-B", 1901, "10.77.2.11"),
            JaceSpec("JACE-9000-C", 1902, "10.77.2.12"),
        ],
        "mstp_devices": [
            MstpSpec("AHU-1", 2100, "ahu", "JACE-9000-A", 1, 100),
            *[MstpSpec(f"VAV-{i}", 2100 + i, "vav", "JACE-9000-A", i + 1, 100) for i in range(1, 9)],
            MstpSpec("AHU-2", 2200, "ahu", "JACE-9000-B", 1, 110),
            *[MstpSpec(f"VAV-{i}", 2200 + (i - 8), "vav", "JACE-9000-B", (i - 8) + 1, 110) for i in range(9, 17)],
            MstpSpec("AHU-3", 2300, "ahu", "JACE-9000-C", 1, 120),
            *[MstpSpec(f"VAV-{i}", 2300 + (i - 16), "vav", "JACE-9000-C", (i - 16) + 1, 120) for i in range(17, 25)],
        ],
    },
    "P3_PLANT_AND_FLOOR_JACES": {
        "project_name": "Plant + Building Integration (JACE plant + JACE floor)",
        "recommended_package": "bacsim_p3_plant_and_floor_jaces_v1",
        "fault_scenarios": [
            "normal_day",
            "fan_fail",
            "sensor_drift",
            "stuck_damper",
            "device_offline",
            "pump_failover",
            "chiller_stage_loss",
        ],
        "jaces": [
            JaceSpec("JACE-PLANT", 1910, "10.77.3.10"),
            JaceSpec("JACE-FLOOR-A", 1911, "10.77.3.11"),
        ],
        "mstp_devices": [
            MstpSpec("Boiler-1", 2400, "boiler", "JACE-PLANT", 1, 130),
            MstpSpec("Chiller-1", 2401, "chiller", "JACE-PLANT", 2, 130),
            MstpSpec("CHW-Pump-1", 2402, "pump", "JACE-PLANT", 3, 130),
            MstpSpec("CHW-Pump-2", 2403, "pump", "JACE-PLANT", 4, 130),
            MstpSpec("HW-Pump-1", 2404, "pump", "JACE-PLANT", 5, 130),
            MstpSpec("AHU-1", 2500, "ahu", "JACE-FLOOR-A", 1, 140),
            *[MstpSpec(f"VAV-{i}", 2500 + i, "vav", "JACE-FLOOR-A", i + 1, 140) for i in range(1, 7)],
        ],
    },
    "P4_RETROFIT_LEGACY_MSTP": {
        "project_name": "Retrofit Legacy Site (legacy names on MS/TP)",
        "recommended_package": "bacsim_p4_retrofit_legacy_mstp_v1",
        "fault_scenarios": [
            "normal_day",
            "fan_fail",
            "sensor_drift",
            "stuck_damper",
            "device_offline",
            "legacy_point_mismatch",
        ],
        "jaces": [JaceSpec("JACE-9000-LEG", 1920, "10.77.4.10")],
        "mstp_devices": [
            MstpSpec("RTU-A-MAIN", 2600, "ahu", "JACE-9000-LEG", 1, 150),
            *[MstpSpec(f"ZN-A{i}", 2600 + i, "vav", "JACE-9000-LEG", i + 1, 150) for i in range(1, 7)],
            MstpSpec("LEGACY-IO-1", 2607, "generic", "JACE-9000-LEG", 8, 150),
        ],
    },
}


def _make_jace_device(spec: JaceSpec) -> DeviceModel:
    return DeviceModel(
        name=spec.name,
        device_instance=spec.device_id,
        vendor_id=999,
        description=f"Gateway {spec.name}",
        enabled=True,
        transport="ip",
        bacnet_ip=spec.ip,
        bacnet_port=47808,
        mstp_parent="",
        mstp_mac=None,
        objects=[],
    )


def _add_cross_device_rules(project: ProjectModel) -> None:
    refs = set(project.all_point_refs())

    def maybe_add(rule: LogicRule) -> None:
        if rule.lhs_ref in refs and rule.action_ref in refs:
            project.logic_rules.append(rule)

    maybe_add(
        LogicRule(
            name="AHU-1 Fan Status Delay",
            lhs_ref="AHU-1.SupplyFanCmd",
            operator="==",
            rhs_value=1,
            action_ref="AHU-1.SupplyFanStatus",
            action_value=1,
            else_value=0,
            delay_seconds=5.0,
            enabled=True,
        )
    )
    maybe_add(
        LogicRule(
            name="AHU-1 Damper Track",
            lhs_ref="AHU-1.SupplyFanCmd",
            operator="==",
            rhs_value=1,
            action_ref="AHU-1.DamperCmd",
            action_value=60,
            else_value=20,
            delay_seconds=0.0,
            enabled=True,
        )
    )
    maybe_add(
        LogicRule(
            name="Boiler-1 Pump Follow Enable",
            lhs_ref="Boiler-1.Enable",
            operator="==",
            rhs_value=1,
            action_ref="Boiler-1.PumpCmd",
            action_value=1,
            else_value=0,
            delay_seconds=0.0,
            enabled=True,
        )
    )


def build_project(project_key: str, spec: dict) -> ProjectModel:
    project = ProjectModel(
        name=f"{project_key} - {spec['project_name']}",
        description=f"Prebuilt book project (JACE + MS/TP): {spec['project_name']}",
        bacnet=BacnetSettings(
            network_name="SimNetwork",
            bind_ip="0.0.0.0",
            base_udp_port=47808,
            interface_alias="",
            auto_manage_ip_aliases=True,
            alias_prefix_length=24,
            remove_auto_aliases_on_exit=False,
        ),
        scenario=ScenarioState(
            occupied=True,
            outdoor_air_temp=55.0,
            alarm_injection=False,
            sensor_failure_refs=[],
        ),
    )

    for jace in spec["jaces"]:
        project.devices.append(_make_jace_device(jace))

    for mstp in spec["mstp_devices"]:
        dev = build_template(
            mstp.template,
            name=mstp.name,
            device_instance=mstp.device_id,
            port=47808,
            ip="",
            transport="mstp",
            mstp_parent=mstp.parent,
            mstp_mac=mstp.mac,
        )
        dev.description = f"{dev.description} (MS/TP net {mstp.mstp_network})"
        dev.metadata = getattr(dev, "metadata", {})
        project.devices.append(dev)

    _add_cross_device_rules(project)
    return project


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Remove older generated files so only current spec set remains.
    for old in OUT_DIR.glob("*.yaml"):
        old.unlink(missing_ok=True)

    for project_key, spec in PROJECT_SPECS.items():
        project = build_project(project_key, spec)
        errors = validate_project(project)
        if errors:
            print(f"Validation failed for {project_key}:")
            for err in errors:
                print(" -", err)
            return 1

        file_name = f"{project_key.lower()}.yaml"
        path = OUT_DIR / file_name
        save_project(project, path)
        print(
            f"Wrote {path} "
            f"(ip_jaces={len(spec['jaces'])}, mstp_devices={len(spec['mstp_devices'])}, total={len(project.devices)})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
