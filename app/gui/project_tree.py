from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMenu, QTreeWidget, QTreeWidgetItem

from app.models.device_model import DeviceModel
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

    @staticmethod
    def _is_mstp(device: DeviceModel) -> bool:
        return (device.transport or "ip").strip().lower() == "mstp"

    @staticmethod
    def _device_label(device: DeviceModel) -> str:
        if (device.transport or "ip").strip().lower() == "mstp":
            mac = "?" if device.mstp_mac is None else str(device.mstp_mac)
            return f"[MS/TP] {device.name} [{device.device_instance}] (mac {mac})"
        return f"[IP] {device.name} [{device.device_instance}]"

    def _item_key(self, item: QTreeWidgetItem | None):
        if item is None:
            return None
        data = item.data(0, Qt.UserRole)
        if not isinstance(data, tuple) or len(data) != 3:
            return None
        return data

    def _walk_items(self, parent_item: QTreeWidgetItem):
        for idx in range(parent_item.childCount()):
            child = parent_item.child(idx)
            yield child
            yield from self._walk_items(child)

    def _capture_ui_state(self) -> tuple[set[tuple], tuple | None]:
        expanded: set[tuple] = set()
        selected = self._item_key(self.currentItem())

        if self.topLevelItemCount() == 0:
            return expanded, selected

        root = self.topLevelItem(0)
        for item in [root, *list(self._walk_items(root))]:
            key = self._item_key(item)
            if key is None:
                continue
            if item.isExpanded():
                expanded.add(key)

        return expanded, selected

    def _restore_ui_state(self, expanded: set[tuple], selected: tuple | None) -> None:
        if self.topLevelItemCount() == 0:
            return

        root = self.topLevelItem(0)
        selected_item: QTreeWidgetItem | None = None

        for item in [root, *list(self._walk_items(root))]:
            key = self._item_key(item)
            if key is None:
                continue
            if key in expanded:
                item.setExpanded(True)
            if selected is not None and key == selected:
                selected_item = item

        if selected_item is not None:
            self.setCurrentItem(selected_item)

    def _add_device_item(self, parent_item: QTreeWidgetItem, device: DeviceModel) -> QTreeWidgetItem:
        device_item = QTreeWidgetItem([self._device_label(device)])
        device_item.setData(0, Qt.UserRole, ("device", device.name, ""))

        if self._is_mstp(device):
            parent = (device.mstp_parent or "").strip() or "<no parent>"
            mac = "?" if device.mstp_mac is None else str(device.mstp_mac)
            device_item.setToolTip(0, f"MS/TP parent: {parent}\nMAC: {mac}")
        else:
            ip = (device.bacnet_ip or "").strip() or "0.0.0.0"
            device_item.setToolTip(0, f"BACnet/IP bind: {ip}:{device.bacnet_port}")

        parent_item.addChild(device_item)

        for point in device.objects:
            point_item = QTreeWidgetItem([f"{point.name} ({point.object_type.value})"])
            point_item.setData(0, Qt.UserRole, ("object", device.name, point.name))
            device_item.addChild(point_item)

        return device_item

    def populate(self, project: ProjectModel) -> None:
        expanded, selected = self._capture_ui_state()

        self.clear()
        root = QTreeWidgetItem([project.name])
        root.setData(0, Qt.UserRole, ("project", project.name, ""))
        self.addTopLevelItem(root)

        devices_by_name = {device.name: device for device in project.devices}
        children_by_parent: dict[str, list[DeviceModel]] = {}
        top_level_devices: list[DeviceModel] = []

        for device in project.devices:
            if self._is_mstp(device):
                parent_name = (device.mstp_parent or "").strip()
                if parent_name and parent_name in devices_by_name:
                    children_by_parent.setdefault(parent_name, []).append(device)
                    continue
            top_level_devices.append(device)

        rendered_children = set()

        for device in top_level_devices:
            parent_item = self._add_device_item(root, device)
            for child in children_by_parent.get(device.name, []):
                self._add_device_item(parent_item, child)
                rendered_children.add(child.name)
            if children_by_parent.get(device.name):
                parent_item.setExpanded(True)

        for device in project.devices:
            if self._is_mstp(device) and device.name not in rendered_children:
                self._add_device_item(root, device)

        root.setExpanded(True)
        self._restore_ui_state(expanded, selected)

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