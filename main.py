from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from app.bacnet.bacnet_manager import BacnetManager
from app.gui.dialogs import AddDeviceDialog, AddObjectDialog
from app.gui.main_window import MainWindow
from app.models.object_model import BehaviorConfig, BehaviorMode, ObjectModel, ObjectType, ScheduleConfig
from app.models.project_model import ProjectModel
from app.models.template_defs import build_template
from app.sim.simulation_engine import SimulationEngine
from app.storage.project_io import load_project, save_project
from app.utils.logging_setup import configure_logging
from app.utils.validators import validate_project


class AppController:
    def __init__(self):
        self.window = MainWindow()
        self.sim = SimulationEngine()
        self.bacnet = BacnetManager()

        self.project = ProjectModel()
        self.current_path: Path | None = None
        self.selected_device_name: str | None = None
        self.selected_object_name: str | None = None

        self._connect_signals()
        self._set_project(self.project)

    def _connect_signals(self) -> None:
        self.window.new_project_requested.connect(self.new_project)
        self.window.open_project_requested.connect(self.open_project)
        self.window.save_project_requested.connect(self.save_project)
        self.window.save_as_project_requested.connect(self.save_project_as)

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

        self.bacnet.status_changed.connect(self.window.log)
        self.bacnet.error.connect(self.window.log)

        self.window.live_table.itemSelectionChanged.connect(self._refresh_selected_trend)

    def _set_project(self, project: ProjectModel) -> None:
        self.project = project
        self.sim.set_project(self.project)
        self.bacnet.set_project(self.project)
        self.window.set_project(self.project)
        self.window.device_editor.set_device(None)
        self.window.object_editor.set_object(None)

    def show(self) -> None:
        self.window.show()

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
            str(Path.cwd()),
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
            str(Path.cwd() / "sample_projects"),
            "YAML Files (*.yaml *.yml)",
        )
        if not selected:
            return
        self.current_path = Path(selected)
        self.save_project()

    def add_device(self) -> None:
        default_instance = 1000 + len(self.project.devices)
        default_port = self.project.bacnet.base_udp_port + len(self.project.devices)
        dialog = AddDeviceDialog(default_instance=default_instance, default_port=default_port, parent=self.window)
        if dialog.exec() != dialog.Accepted:
            return
        data = dialog.result_data()
        if not data:
            return

        device = build_template(
            data["template"],
            data["name"],
            data["instance"],
            data["port"],
        )
        self.project.devices.append(device)
        self.window.set_project(self.project)
        self.window.log(f"Added device {device.name} from template {data['template']}.")

    def add_object(self, device_name: str) -> None:
        device = self.project.get_device(device_name)
        if device is None:
            return
        next_instance = max([obj.instance for obj in device.objects] + [0]) + 1
        dialog = AddObjectDialog(next_instance=next_instance, parent=self.window)
        if dialog.exec() != dialog.Accepted:
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
        self.window.set_project(self.project)
        self.window.log(f"Added object {device.name}.{obj.name}.")

    def delete_device(self, device_name: str) -> None:
        self.project.devices = [device for device in self.project.devices if device.name != device_name]
        self.window.set_project(self.project)
        self.window.log(f"Deleted device {device_name}.")

    def delete_object(self, device_name: str, object_name: str) -> None:
        device = self.project.get_device(device_name)
        if not device:
            return
        device.remove_object(object_name)
        self.window.set_project(self.project)
        self.window.log(f"Deleted object {device_name}.{object_name}.")

    def _on_device_selected(self, device_name: str) -> None:
        self.selected_device_name = device_name
        self.selected_object_name = None
        device = self.project.get_device(device_name)
        self.window.device_editor.set_device(device)
        self.window.object_editor.set_object(None)

    def _on_object_selected(self, device_name: str, object_name: str) -> None:
        self.selected_device_name = device_name
        self.selected_object_name = object_name
        device = self.project.get_device(device_name)
        obj = device.get_object(object_name) if device else None
        self.window.object_editor.set_object(obj)
        point_ref = f"{device_name}.{object_name}"
        self.window.select_live_point(point_ref)
        self._refresh_selected_trend()

    def _on_device_saved(self) -> None:
        self.window.set_project(self.project)
        self.window.log("Device changes saved.")

    def _on_object_saved(self) -> None:
        self.window.set_project(self.project)
        self.window.log("Object changes saved.")

    def start_simulation(self) -> None:
        self.sim.start()
        self.bacnet.start()

    def stop_simulation(self) -> None:
        self.sim.stop()
        self.bacnet.stop()

    def _reset_sim(self) -> None:
        self.sim.reset_values()
        self.window.set_project(self.project)

    def _on_tick(self, snapshot: dict[str, float]) -> None:
        self.window.update_live_values(snapshot)
        self.bacnet.notify_simulation_tick()
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

    sample = Path(__file__).resolve().parent / "sample_projects" / "training_lab.yaml"
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

