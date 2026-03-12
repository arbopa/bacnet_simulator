from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models.device_model import DeviceModel


class DeviceEditor(QWidget):
    saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._device: DeviceModel | None = None

        self.name_edit = QLineEdit()
        self.instance_spin = QSpinBox()
        self.instance_spin.setMaximum(4_194_302)
        self.vendor_spin = QSpinBox()
        self.vendor_spin.setMaximum(65_535)
        self.description_edit = QLineEdit()
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.enabled_check = QCheckBox("Enabled")
        self.object_count_label = QLabel("0")
        self.online_label = QLabel("Offline")

        form = QFormLayout()
        form.addRow("Device Name", self.name_edit)
        form.addRow("Device Instance", self.instance_spin)
        form.addRow("Vendor ID", self.vendor_spin)
        form.addRow("Description", self.description_edit)
        form.addRow("UDP Port", self.port_spin)
        form.addRow("Object Count", self.object_count_label)
        form.addRow("BACnet Status", self.online_label)
        form.addRow("", self.enabled_check)

        save_btn = QPushButton("Save Device")
        save_btn.clicked.connect(self._save)

        box = QGroupBox("Device Editor")
        box.setLayout(form)

        layout = QVBoxLayout(self)
        layout.addWidget(box)
        row = QHBoxLayout()
        row.addWidget(save_btn)
        row.addStretch(1)
        layout.addLayout(row)

    def set_online(self, online: bool) -> None:
        self.online_label.setText("Online" if online else "Offline")

    def set_device(self, device: DeviceModel | None) -> None:
        self._device = device
        enabled = device is not None
        for widget in [
            self.name_edit,
            self.instance_spin,
            self.vendor_spin,
            self.description_edit,
            self.port_spin,
            self.enabled_check,
        ]:
            widget.setEnabled(enabled)
        if not device:
            self.name_edit.setText("")
            self.object_count_label.setText("0")
            return

        self.name_edit.setText(device.name)
        self.instance_spin.setValue(device.device_instance)
        self.vendor_spin.setValue(device.vendor_id)
        self.description_edit.setText(device.description)
        self.port_spin.setValue(device.bacnet_port)
        self.enabled_check.setChecked(device.enabled)
        self.object_count_label.setText(str(device.object_count))

    def _save(self) -> None:
        if not self._device:
            return
        self._device.name = self.name_edit.text().strip()
        self._device.device_instance = self.instance_spin.value()
        self._device.vendor_id = self.vendor_spin.value()
        self._device.description = self.description_edit.text().strip()
        self._device.bacnet_port = self.port_spin.value()
        self._device.enabled = self.enabled_check.isChecked()
        self.saved.emit()
