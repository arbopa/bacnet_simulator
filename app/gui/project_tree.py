from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMenu, QTreeWidget, QTreeWidgetItem

from app.models.project_model import ProjectModel


class ProjectTree(QTreeWidget):
    device_selected = Signal(str)
    object_selected = Signal(str, str)
    add_device_requested = Signal()
    add_object_requested = Signal(str)
    delete_device_requested = Signal(str)
    delete_object_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("System")
        self.itemClicked.connect(self._handle_item_clicked)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def populate(self, project: ProjectModel) -> None:
        self.clear()
        root = QTreeWidgetItem([project.name])
        root.setData(0, Qt.UserRole, ("project", project.name, ""))
        self.addTopLevelItem(root)

        for device in project.devices:
            device_item = QTreeWidgetItem([f"{device.name} [{device.device_instance}]"])
            device_item.setData(0, Qt.UserRole, ("device", device.name, ""))
            root.addChild(device_item)

            for point in device.objects:
                point_item = QTreeWidgetItem([f"{point.name} ({point.object_type.value})"])
                point_item.setData(0, Qt.UserRole, ("object", device.name, point.name))
                device_item.addChild(point_item)

        root.setExpanded(True)

    def _handle_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        kind, device_name, object_name = item.data(0, Qt.UserRole)
        if kind == "device":
            self.device_selected.emit(device_name)
        elif kind == "object":
            self.object_selected.emit(device_name, object_name)

    def _show_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        menu = QMenu(self)
        if item is None:
            action = menu.addAction("Add Device")
            action.triggered.connect(self.add_device_requested.emit)
            menu.exec(self.viewport().mapToGlobal(pos))
            return

        kind, device_name, object_name = item.data(0, Qt.UserRole)
        if kind == "project":
            menu.addAction("Add Device", self.add_device_requested.emit)
        elif kind == "device":
            menu.addAction("Add Object", lambda: self.add_object_requested.emit(device_name))
            menu.addAction("Delete Device", lambda: self.delete_device_requested.emit(device_name))
        elif kind == "object":
            menu.addAction("Delete Object", lambda: self.delete_object_requested.emit(device_name, object_name))

        menu.exec(self.viewport().mapToGlobal(pos))
