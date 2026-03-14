from __future__ import annotations

from pathlib import Path

from app.models.device_model import DeviceModel
from app.models.project_model import BacnetSettings, LogicRule, ProjectModel, ScenarioState
from app.models.template_defs import build_template
from app.storage.project_io import save_project
from app.utils.validators import validate_project


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "sample_projects" / "training_lab.yaml"


def main() -> int:
    project = ProjectModel(
        name="Training Lab Building",
        description="Virtual BAS lab for Niagara BACnet training.",
        bacnet=BacnetSettings(
            network_name="SimNetwork",
            bind_ip="0.0.0.0",
            base_udp_port=47808,
            interface_alias="Ethernet 2",
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

    project.devices.extend(
        [
            DeviceModel(
                name="JACE-9000-A",
                device_instance=1900,
                vendor_id=999,
                description="Gateway JACE-9000 A",
                transport="ip",
                bacnet_ip="10.0.0.114",
                bacnet_port=47808,
                objects=[],
            ),
            DeviceModel(
                name="JACE-9000-B",
                device_instance=1901,
                vendor_id=999,
                description="Gateway JACE-9000 B",
                transport="ip",
                bacnet_ip="10.0.0.115",
                bacnet_port=47808,
                objects=[],
            ),
            DeviceModel(
                name="JACE-9000-C",
                device_instance=1902,
                vendor_id=999,
                description="Gateway JACE-9000 C",
                transport="ip",
                bacnet_ip="10.0.0.116",
                bacnet_port=47808,
                objects=[],
            ),
        ]
    )

    project.devices.append(
        build_template(
            "ahu",
            name="AHU-1",
            device_instance=2000,
            port=47808,
            transport="mstp",
            mstp_parent="JACE-9000-A",
            mstp_mac=1,
        )
    )

    for i in range(1, 16):
        project.devices.append(
            build_template(
                "vav",
                name=f"VAV-{i}",
                device_instance=2000 + i,
                port=47808,
                transport="mstp",
                mstp_parent="JACE-9000-A",
                mstp_mac=i + 1,
            )
        )

    project.devices.append(
        build_template(
            "boiler",
            name="Boiler-1",
            device_instance=2016,
            port=47808,
            transport="mstp",
            mstp_parent="JACE-9000-B",
            mstp_mac=1,
        )
    )
    project.devices.append(
        build_template(
            "chiller",
            name="Chiller-1",
            device_instance=2017,
            port=47808,
            transport="mstp",
            mstp_parent="JACE-9000-B",
            mstp_mac=2,
        )
    )
    project.devices.append(
        build_template(
            "pump",
            name="PumpPanel-1",
            device_instance=2018,
            port=47808,
            transport="mstp",
            mstp_parent="JACE-9000-B",
            mstp_mac=3,
        )
    )

    project.devices.append(
        build_template(
            "generic",
            name="GFC-1",
            device_instance=2019,
            port=47808,
            transport="mstp",
            mstp_parent="JACE-9000-C",
            mstp_mac=1,
        )
    )
    project.devices.append(
        build_template(
            "generic",
            name="GFC-2",
            device_instance=2020,
            port=47808,
            transport="mstp",
            mstp_parent="JACE-9000-C",
            mstp_mac=2,
        )
    )
    project.devices.append(
        build_template(
            "generic",
            name="GFC-3",
            device_instance=2021,
            port=47808,
            transport="mstp",
            mstp_parent="JACE-9000-C",
            mstp_mac=3,
        )
    )

    project.logic_rules = [
        LogicRule(
            name="AHU Fan Status Delay",
            lhs_ref="AHU-1.SupplyFanCmd",
            operator="==",
            rhs_value=1,
            action_ref="AHU-1.SupplyFanStatus",
            action_value=1,
            else_value=0,
            delay_seconds=5.0,
            enabled=True,
        ),
        LogicRule(
            name="AHU Damper Track",
            lhs_ref="AHU-1.SupplyFanCmd",
            operator="==",
            rhs_value=1,
            action_ref="AHU-1.DamperCmd",
            action_value=60,
            else_value=20,
            delay_seconds=0.0,
            enabled=True,
        ),
        LogicRule(
            name="Boiler Pump Follow Enable",
            lhs_ref="Boiler-1.Enable",
            operator="==",
            rhs_value=1,
            action_ref="Boiler-1.PumpCmd",
            action_value=1,
            else_value=0,
            delay_seconds=0.0,
            enabled=True,
        ),
    ]

    errors = validate_project(project)
    if errors:
        print("Validation errors:")
        for err in errors:
            print(" -", err)
        return 1

    save_project(project, OUT_PATH)
    print(f"Wrote {OUT_PATH} with {len(project.devices)} devices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())