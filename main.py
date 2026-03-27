from __future__ import annotations

import ipaddress
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog

from app.gui.dialogs import AddDeviceDialog, AddObjectDialog, NetworkSetupDialog
from app.gui.main_window import MainWindow
from app.models.object_model import BehaviorConfig, BehaviorMode, ObjectModel, ObjectType, ScheduleConfig
from app.models.project_model import ProjectModel
from app.models.template_defs import build_template
from app.protocol import BacnetProtocolAdapter, ModbusProtocolAdapter, MqttProtocolAdapter, ProtocolManager
from app.sim.simulation_engine import SimulationEngine
from app.storage.project_io import load_project, save_project
from app.utils.ip_alias_manager import IPAliasManager
from app.utils.logging_setup import configure_logging
from app.utils.validators import validate_project

def app_root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", app_root_dir()))
    return base.joinpath(*parts)


class AppController:
    def __init__(self):
        self.window = MainWindow()
        self.sim = SimulationEngine()
        self.protocols = ProtocolManager()
        self.protocols.register_adapter(BacnetProtocolAdapter(parent=self.protocols))
        self.protocols.register_adapter(ModbusProtocolAdapter(parent=self.protocols))
        self.protocols.register_adapter(MqttProtocolAdapter(parent=self.protocols))

        self.project = ProjectModel()
        self.current_path: Path | None = None
        self.selected_device_name: str | None = None
        self.selected_object_name: str | None = None
        self._session_created_aliases: dict[str, set[str]] = {}
        self._startup_failure_alerted = False

        self._connect_signals()
        self._set_project(self.project)

    def _connect_signals(self) -> None:
        self.window.new_project_requested.connect(self.new_project)
        self.window.open_project_requested.connect(self.open_project)
        self.window.save_project_requested.connect(self.save_project)
        self.window.save_as_project_requested.connect(self.save_project_as)
        self.window.network_setup_requested.connect(self.configure_network)

        self.window.start_sim_requested.connect(self.start_simulation)
        self.window.stop_sim_requested.connect(self.stop_simulation)
        self.window.pause_sim_requested.connect(self.sim.pause)
        self.window.resume_sim_requested.connect(self.sim.resume)
        self.window.reset_sim_requested.connect(self._reset_sim)

        self.window.project_tree.device_selected.connect(self._on_device_selected)
        self.window.project_tree.object_selected.connect(self._on_object_selected)
        self.window.project_tree.add_device_requested.connect(self.add_device)
        self.window.project_tree.add_object_requested.connect(self.add_object)
        self.window.project_tree.delete_device_requested.connect(self.delete_device)
        self.window.project_tree.delete_object_requested.connect(self.delete_object)

        self.window.device_editor.saved.connect(self._on_device_saved)
        self.window.object_editor.saved.connect(self._on_object_saved)

        self.sim.tick_completed.connect(self._on_tick)
        self.sim.message.connect(self.window.log)
        self.sim.started.connect(lambda: self.window.log("Simulation running."))
        self.sim.stopped.connect(lambda: self.window.log("Simulation stopped."))

        self.protocols.message.connect(self._on_protocol_message)

        self.window.live_table.itemSelectionChanged.connect(self._refresh_selected_trend)

    def _set_project(self, project: ProjectModel) -> None:
        self.project = project
        self.sim.set_project(self.project)
        self.protocols.set_project(self.project)
        self.protocols.set_registry(self.sim.registry)
        self.window.set_project(self.project)
        self.window.device_editor.set_device(None)
        self.window.object_editor.set_device_context("", [])
        self.window.object_editor.set_object(None)

    def show(self) -> None:
        self.window.show()

    def _on_protocol_message(self, message: str) -> None:
        self.window.log(message)

        if message.startswith("[bacnet] unavailable in current environment"):
            if self.sim.running:
                self.window.log("[network] BACnet unavailable; auto-stopping simulation.")
                self.stop_simulation()
            if not self._startup_failure_alerted:
                self._startup_failure_alerted = True
                QMessageBox.critical(self.window, "BACnet Unavailable", message)
            return

        if not message.startswith("[bacnet] BACnet start failed"):
            return
        if self.sim.running:
            self.window.log("[network] BACnet startup failed; auto-stopping simulation.")
            self.stop_simulation()
        if not self._startup_failure_alerted:
            self._startup_failure_alerted = True
            QMessageBox.critical(self.window, "BACnet Startup Failed", message)
        return

    def _refresh_runtime_registry(self) -> None:
        self.sim.rebuild_runtime_registry()
        self.protocols.set_registry(self.sim.registry)

    def _persist_project_if_loaded(self, reason: str) -> None:
        if self.current_path is None:
            return
        try:
            save_project(self.project, self.current_path)
            self.window.log(f"Project auto-saved ({reason}): {self.current_path}")
        except Exception as err:
            self.window.log(f"Project auto-save failed ({reason}): {err}")

    def new_project(self) -> None:
        self.stop_simulation()
        self.current_path = None
        self.selected_device_name = None
        self.selected_object_name = None
        self._set_project(ProjectModel())
        self.window.log("New project created.")

    def open_project(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self.window,
            "Open Project",
            str(app_root_dir()),
            "YAML Files (*.yaml *.yml)",
        )
        if not selected:
            return
        path = Path(selected)
        project = load_project(path)
        self.current_path = path
        self._set_project(project)
        self.window.log(f"Project opened: {path}")

    def save_project(self) -> None:
        if self.current_path is None:
            self.save_project_as()
            return
        errors = validate_project(self.project)
        if errors:
            QMessageBox.warning(self.window, "Validation Errors", "\n".join(errors))
            return
        save_project(self.project, self.current_path)
        self.window.log(f"Project saved: {self.current_path}")

    def save_project_as(self) -> None:
        selected, _ = QFileDialog.getSaveFileName(
            self.window,
            "Save Project As",
            str(app_root_dir() / "sample_projects"),
            "YAML Files (*.yaml *.yml)",
        )
        if not selected:
            return
        self.current_path = Path(selected)
        self.save_project()

    def _target_ip_aliases(self) -> list[str]:
        return sorted(
            {
                (device.bacnet_ip or "").strip()
                for device in self.project.devices
                if (device.transport or "ip").strip().lower() == "ip"
                and (device.bacnet_ip or "").strip()
                and (device.bacnet_ip or "").strip() != "0.0.0.0"
            }
        )

    def _remember_created_aliases(self, adapter: str, created_ips: list[str]) -> None:
        if not created_ips:
            return
        alias_set = self._session_created_aliases.setdefault(adapter, set())
        alias_set.update(created_ips)

    def _resolve_selected_adapter_bind_ip(self) -> str:
        adapter = (self.project.bacnet.interface_alias or "").strip()
        if not adapter:
            return ""
        return IPAliasManager.preferred_ipv4(adapter)

    @staticmethod
    def _is_valid_ipv4(ip: str) -> bool:
        try:
            return isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)
        except Exception:
            return False

    def _validate_and_prepare_bacnet_bind(self, *, show_dialog: bool) -> bool:
        settings = self.project.bacnet
        adapter = (settings.interface_alias or "").strip()
        if not adapter:
            msg = "[network] BACnet start blocked: no adapter selected."
            self.window.log(msg)
            if show_dialog:
                QMessageBox.warning(self.window, "Network Setup", msg)
            return False

        bind_ip = self._resolve_selected_adapter_bind_ip()
        if not bind_ip or (not self._is_valid_ipv4(bind_ip)):
            msg = (
                f"[network] BACnet start blocked: selected adapter '{adapter}' has no usable IPv4 address."
            )
            self.window.log(msg)
            if show_dialog:
                QMessageBox.warning(self.window, "Network Setup", msg)
            return False

        adapter_ips = set(IPAliasManager.list_ipv4_addresses(adapter))
        if bind_ip not in adapter_ips:
            msg = (
                f"[network] BACnet start blocked: selected bind IP {bind_ip} is not present on adapter '{adapter}'."
            )
            self.window.log(msg)
            if show_dialog:
                QMessageBox.warning(self.window, "Network Setup", msg)
            return False

        invalid_devices: list[str] = []
        for device in self.project.devices:
            if not device.enabled:
                continue
            if (device.transport or "ip").strip().lower() != "ip":
                continue
            device_ip = (device.bacnet_ip or "").strip()
            if not device_ip or device_ip == "0.0.0.0":
                continue
            if not self._is_valid_ipv4(device_ip):
                invalid_devices.append(f"{device.name}={device_ip} (invalid IPv4)")
                continue
            if device_ip not in adapter_ips:
                invalid_devices.append(f"{device.name}={device_ip}")

        if invalid_devices:
            sample = ", ".join(invalid_devices[:8])
            msg = (
                f"[network] BACnet start blocked: IP device address(es) not on selected adapter '{adapter}': {sample}"
            )
            self.window.log(msg)
            if show_dialog:
                QMessageBox.warning(self.window, "Network Setup", msg)
            return False

        settings.bind_ip = bind_ip
        self.window.log(f"[network] Adapter '{adapter}' authoritative bind IP resolved to {bind_ip}.")
        return True

    def _apply_ip_aliases(self, *, show_dialog: bool) -> bool:
        settings = self.project.bacnet
        if not settings.auto_manage_ip_aliases:
            return True

        adapter = (settings.interface_alias or "").strip()
        if not adapter:
            msg = "[network] Auto-manage IP aliases is enabled, but no adapter is selected."
            self.window.log(msg)
            if show_dialog:
                QMessageBox.warning(self.window, "Network Setup", msg)
            return False

        if not IPAliasManager.has_non_manual_ipv4(adapter):
            msg = (
                f"[network] Adapter '{adapter}' has no non-manual IPv4 address. "
                "Alias application can disrupt normal connectivity."
            )
            self.window.log(msg)
            if show_dialog:
                QMessageBox.warning(self.window, "Network Setup Warning", msg)

        ips = self._target_ip_aliases()
        if not ips:
            msg = "[network] No explicit BACnet/IP device aliases to apply."
            self.window.log(msg)
            if show_dialog:
                QMessageBox.information(self.window, "Network Setup", msg)
            return True

        result = IPAliasManager.ensure_ip_aliases(adapter, ips, prefix_length=settings.alias_prefix_length)
        self._remember_created_aliases(adapter, result.created_ips)

        summary = (
            f"[network] Alias apply complete on '{adapter}': requested={len(result.requested_ips)} "
            f"created={len(result.created_ips)} existing={len(result.existing_ips)} errors={len(result.errors)}"
        )
        self.window.log(summary)
        for err in result.errors:
            self.window.log(f"[network] {err}")

        if show_dialog:
            details = [summary]
            if result.created_ips:
                details.append(f"Created: {', '.join(result.created_ips)}")
            if result.errors:
                details.append("Errors:")
                details.extend(result.errors[:8])
            QMessageBox.information(self.window, "Network Setup", "\n".join(details))

        return len(result.errors) == 0

    def _cleanup_created_aliases_on_exit(self) -> None:
        settings = self.project.bacnet
        if not settings.remove_auto_aliases_on_exit:
            return

        for adapter, aliases in list(self._session_created_aliases.items()):
            if not aliases:
                continue
            remove_result = IPAliasManager.remove_ip_aliases(adapter, sorted(aliases))
            self.window.log(
                f"[network] Alias cleanup on '{adapter}': requested={len(remove_result.requested_ips)} "
                f"removed={len(remove_result.removed_ips)} missing={len(remove_result.missing_ips)} "
                f"errors={len(remove_result.errors)}"
            )
            for err in remove_result.errors:
                self.window.log(f"[network] cleanup error: {err}")

        self._session_created_aliases.clear()

    def on_app_about_to_quit(self) -> None:
        self.stop_simulation()
        self._cleanup_created_aliases_on_exit()

    def configure_network(self) -> None:
        adapters = IPAliasManager.list_adapters()
        dialog = NetworkSetupDialog(
            adapter_names=adapters,
            current_adapter=self.project.bacnet.interface_alias,
            auto_manage_aliases=self.project.bacnet.auto_manage_ip_aliases,
            alias_prefix_length=self.project.bacnet.alias_prefix_length,
            remove_aliases_on_exit=self.project.bacnet.remove_auto_aliases_on_exit,
            parent=self.window,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.result_data()
        if not data:
            return

        self.project.bacnet.interface_alias = data["interface_alias"]
        self.project.bacnet.auto_manage_ip_aliases = bool(data["auto_manage_ip_aliases"])
        self.project.bacnet.alias_prefix_length = int(data["alias_prefix_length"])
        self.project.bacnet.remove_auto_aliases_on_exit = bool(data["remove_auto_aliases_on_exit"])
        resolved_bind = self._resolve_selected_adapter_bind_ip()
        if resolved_bind:
            self.project.bacnet.bind_ip = resolved_bind

        mode = "enabled" if self.project.bacnet.auto_manage_ip_aliases else "disabled"
        cleanup_mode = "enabled" if self.project.bacnet.remove_auto_aliases_on_exit else "disabled"
        adapter = self.project.bacnet.interface_alias or "<none>"
        self.window.log(
            f"Network setup saved: auto alias {mode}, cleanup-on-exit {cleanup_mode}, "
            f"adapter={adapter}, bind_ip={self.project.bacnet.bind_ip}, /{self.project.bacnet.alias_prefix_length}."
        )
        self._persist_project_if_loaded("network settings")

        if self.project.bacnet.auto_manage_ip_aliases:
            self._apply_ip_aliases(show_dialog=True)

    def add_device(self) -> None:
        default_instance = 1000 + len(self.project.devices)
        default_port = self.project.bacnet.base_udp_port + len(self.project.devices)
        dialog = AddDeviceDialog(default_instance=default_instance, default_port=default_port, parent=self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.result_data()
        if not data:
            return

        device = build_template(
            data["template"],
            data["name"],
            data["instance"],
            data["port"],
            data["ip"],
            transport=data["transport"],
            mstp_parent=data["mstp_parent"],
            mstp_mac=data["mstp_mac"],
        )
        self.project.devices.append(device)
        self._refresh_runtime_registry()
        self.window.set_project(self.project)
        self.window.log(f"Added device {device.name} from template {data['template']}.")

    def add_object(self, device_name: str) -> None:
        device = self.project.get_device(device_name)
        if device is None:
            return
        next_instance = max([obj.instance for obj in device.objects] + [0]) + 1
        dialog = AddObjectDialog(next_instance=next_instance, parent=self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.result_data()
        if not data:
            return

        obj_type = ObjectType(data["object_type"])
        writable = obj_type in {
            ObjectType.ANALOG_OUTPUT,
            ObjectType.ANALOG_VALUE,
            ObjectType.BINARY_OUTPUT,
            ObjectType.BINARY_VALUE,
            ObjectType.MULTI_STATE_VALUE,
            ObjectType.SCHEDULE,
        }

        obj = ObjectModel(
            instance=data["instance"],
            name=data["name"],
            object_type=obj_type,
            writable=writable,
            present_value=0.0,
            initial_value=0.0,
            behavior=BehaviorConfig(mode=BehaviorMode.MANUAL),
            schedule=ScheduleConfig(),
        )

        if obj_type == ObjectType.SCHEDULE:
            obj.behavior.mode = BehaviorMode.SCHEDULE
            obj.present_value = 1.0
            obj.initial_value = 1.0
        if obj_type == ObjectType.TREND_LOG:
            obj.writable = False
            obj.metadata["source_ref"] = ""

        device.objects.append(obj)
        self._refresh_runtime_registry()
        self.window.set_project(self.project)
        self.window.log(f"Added object {device.name}.{obj.name}.")

    def delete_device(self, device_name: str) -> None:
        self.project.devices = [device for device in self.project.devices if device.name != device_name]
        self._refresh_runtime_registry()
        self.window.set_project(self.project)
        self.window.log(f"Deleted device {device_name}.")

    def delete_object(self, device_name: str, object_name: str) -> None:
        device = self.project.get_device(device_name)
        if not device:
            return
        device.remove_object(object_name)
        self._refresh_runtime_registry()
        self.window.set_project(self.project)
        self.window.log(f"Deleted object {device_name}.{object_name}.")

    def _on_device_selected(self, device_name: str) -> None:
        self.selected_device_name = device_name
        self.selected_object_name = None
        device = self.project.get_device(device_name)
        self.window.device_editor.set_device(device)
        point_names = [obj.name for obj in device.objects] if device else []
        self.window.object_editor.set_device_context(device_name if device else "", point_names)
        self.window.object_editor.set_object(None)

    def _on_object_selected(self, device_name: str, object_name: str) -> None:
        self.selected_device_name = device_name
        self.selected_object_name = object_name
        device = self.project.get_device(device_name)
        obj = device.get_object(object_name) if device else None
        point_names = [item.name for item in device.objects] if device else []
        self.window.object_editor.set_device_context(device_name if device else "", point_names)
        self.window.object_editor.set_object(obj)
        point_ref = f"{device_name}.{object_name}"
        self.window.select_live_point(point_ref)
        self._refresh_selected_trend()

    def _on_device_saved(self) -> None:
        self._refresh_runtime_registry()
        self.window.set_project(self.project)
        self.window.log("Device changes saved.")

    def _on_object_saved(self) -> None:
        self._refresh_runtime_registry()

        if self.selected_device_name and self.selected_object_name:
            device = self.project.get_device(self.selected_device_name)
            obj = device.get_object(self.selected_object_name) if device else None
            if obj is not None:
                point_ref = f"{self.selected_device_name}.{self.selected_object_name}"
                self.sim.registry.mark_dirty(point_ref)

        self.window.set_project(self.project)
        self.window.log("Object changes saved.")

    def start_simulation(self) -> None:
        self._startup_failure_alerted = False
        if not self._apply_ip_aliases(show_dialog=False):
            self.window.log("[network] BACnet start blocked due to alias setup errors.")
            return

        if not self._validate_and_prepare_bacnet_bind(show_dialog=True):
            return

        adapter = (self.project.bacnet.interface_alias or "").strip() or "<none>"
        ports = sorted(
            {
                int(device.bacnet_port)
                for device in self.project.devices
                if device.enabled and (device.transport or "ip").strip().lower() == "ip"
            }
        )
        port_text = ", ".join(str(port) for port in ports) if ports else "<none>"

        self._persist_project_if_loaded("resolved BACnet bind")
        self.window.log(
            f"[network] Startup checkpoint: selected adapter={adapter}, resolved bind_ip={self.project.bacnet.bind_ip}, requested_udp_ports={port_text}"
        )
        self.window.log(
            f"[network] BACnet startup validation: Bound to {self.project.bacnet.bind_ip}:{self.project.bacnet.base_udp_port}"
        )
        self.sim.start()
        self.protocols.start()
    def stop_simulation(self) -> None:
        self.sim.stop()
        self.protocols.stop()

    def _reset_sim(self) -> None:
        self.sim.reset_values()
        self.window.set_project(self.project)

    def _on_tick(self, snapshot: dict[str, float]) -> None:
        self.window.update_live_values(snapshot)
        self.protocols.notify_simulation_tick()
        self._refresh_selected_trend()

    def _refresh_selected_trend(self) -> None:
        point_ref = self.window.selected_point_ref()
        if not point_ref and self.selected_device_name and self.selected_object_name:
            point_ref = f"{self.selected_device_name}.{self.selected_object_name}"
        if not point_ref:
            return
        self.window.trend_view.set_title(point_ref)
        self.window.trend_view.update_samples(self.sim.get_trend(point_ref, last_n=600))


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)

    controller = AppController()
    app.aboutToQuit.connect(controller.on_app_about_to_quit)

    sample = bundled_resource_path("sample_projects", "training_lab.yaml")
    if sample.exists():
        try:
            controller.current_path = sample
            controller._set_project(load_project(sample))
            controller.window.log(f"Loaded sample project: {sample}")
        except Exception as err:
            controller.window.log(f"Sample project failed to load: {err}")

    controller.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

