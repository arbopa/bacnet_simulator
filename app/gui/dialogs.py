from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.models.object_model import ObjectType
from app.models.template_defs import template_choices


class AddDeviceDialog(QDialog):
    def __init__(self, default_instance: int, default_port: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Device")

        self.template_combo = QComboBox()
        for label, key in template_choices():
            self.template_combo.addItem(label, key)

        self.name_edit = QLineEdit("NewDevice")
        self.instance_spin = QSpinBox()
        self.instance_spin.setRange(1, 4_194_302)
        self.instance_spin.setValue(default_instance)

        self.transport_combo = QComboBox()
        self.transport_combo.addItem("BACnet/IP", "ip")
        self.transport_combo.addItem("BACnet MS/TP", "mstp")
        self.transport_combo.currentIndexChanged.connect(self._apply_transport_mode)

        self.ip_edit = QLineEdit("0.0.0.0")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(default_port)

        self.mstp_parent_edit = QLineEdit("")
        self.mstp_parent_edit.setPlaceholderText("Parent IP device name")
        self.mstp_mac_spin = QSpinBox()
        self.mstp_mac_spin.setRange(0, 127)
        self.mstp_mac_spin.setValue(1)

        form = QFormLayout()
        form.addRow("Template", self.template_combo)
        form.addRow("Device Name", self.name_edit)
        form.addRow("Device Instance", self.instance_spin)
        form.addRow("Transport", self.transport_combo)
        form.addRow("BACnet IP", self.ip_edit)
        form.addRow("UDP Port", self.port_spin)
        form.addRow("MS/TP Parent", self.mstp_parent_edit)
        form.addRow("MS/TP MAC", self.mstp_mac_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._apply_transport_mode()

    def _apply_transport_mode(self) -> None:
        is_ip = self.transport_combo.currentData() == "ip"
        self.ip_edit.setEnabled(is_ip)
        self.port_spin.setEnabled(is_ip)
        self.mstp_parent_edit.setEnabled(not is_ip)
        self.mstp_mac_spin.setEnabled(not is_ip)

    def result_data(self) -> Optional[dict]:
        if self.result() != QDialog.Accepted:
            return None

        transport = str(self.transport_combo.currentData() or "ip")
        return {
            "template": self.template_combo.currentData(),
            "name": self.name_edit.text().strip(),
            "instance": self.instance_spin.value(),
            "transport": transport,
            "ip": (self.ip_edit.text().strip() or "0.0.0.0") if transport == "ip" else "",
            "port": self.port_spin.value(),
            "mstp_parent": self.mstp_parent_edit.text().strip(),
            "mstp_mac": self.mstp_mac_spin.value(),
        }


class NetworkSetupDialog(QDialog):
    def __init__(
        self,
        adapter_names: list[str],
        current_adapter: str,
        auto_manage_aliases: bool,
        alias_prefix_length: int,
        remove_aliases_on_exit: bool,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Network Setup")

        self.adapter_combo = QComboBox()
        self.adapter_combo.addItem("<none>", "")
        for name in adapter_names:
            self.adapter_combo.addItem(name, name)

        if current_adapter and (self.adapter_combo.findData(current_adapter) < 0):
            self.adapter_combo.addItem(f"{current_adapter} (saved)", current_adapter)

        current_index = self.adapter_combo.findData(current_adapter)
        if current_index >= 0:
            self.adapter_combo.setCurrentIndex(current_index)

        self.auto_manage_check = QCheckBox("Auto-manage IP aliases for BACnet/IP devices")
        self.auto_manage_check.setChecked(auto_manage_aliases)

        self.remove_on_exit_check = QCheckBox("Remove app-created aliases on exit")
        self.remove_on_exit_check.setChecked(remove_aliases_on_exit)

        self.prefix_spin = QSpinBox()
        self.prefix_spin.setRange(1, 32)
        self.prefix_spin.setValue(int(alias_prefix_length or 24))

        form = QFormLayout()
        form.addRow("Ethernet Adapter", self.adapter_combo)
        form.addRow("Auto Alias", self.auto_manage_check)
        form.addRow("Alias Prefix Length", self.prefix_spin)
        form.addRow("Cleanup On Exit", self.remove_on_exit_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def result_data(self) -> Optional[dict]:
        if self.result() != QDialog.Accepted:
            return None
        return {
            "interface_alias": str(self.adapter_combo.currentData() or ""),
            "auto_manage_ip_aliases": bool(self.auto_manage_check.isChecked()),
            "alias_prefix_length": int(self.prefix_spin.value()),
            "remove_auto_aliases_on_exit": bool(self.remove_on_exit_check.isChecked()),
        }


class AddObjectDialog(QDialog):
    def __init__(self, next_instance: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Object")

        self.name_edit = QLineEdit("NewPoint")
        self.type_combo = QComboBox()
        self.type_combo.addItems(
            [
                ObjectType.ANALOG_INPUT.value,
                ObjectType.ANALOG_OUTPUT.value,
                ObjectType.ANALOG_VALUE.value,
                ObjectType.BINARY_INPUT.value,
                ObjectType.BINARY_OUTPUT.value,
                ObjectType.BINARY_VALUE.value,
                ObjectType.MULTI_STATE_VALUE.value,
                ObjectType.SCHEDULE.value,
                ObjectType.TREND_LOG.value,
            ]
        )
        self.instance_spin = QSpinBox()
        self.instance_spin.setRange(1, 4_194_302)
        self.instance_spin.setValue(next_instance)

        form = QFormLayout()
        form.addRow("Object Name", self.name_edit)
        form.addRow("Object Type", self.type_combo)
        form.addRow("Object Instance", self.instance_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def result_data(self) -> Optional[dict]:
        if self.result() != QDialog.Accepted:
            return None
        return {
            "name": self.name_edit.text().strip(),
            "object_type": self.type_combo.currentText(),
            "instance": self.instance_spin.value(),
        }
