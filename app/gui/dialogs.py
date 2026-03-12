from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
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
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(default_port)

        form = QFormLayout()
        form.addRow("Template", self.template_combo)
        form.addRow("Device Name", self.name_edit)
        form.addRow("Device Instance", self.instance_spin)
        form.addRow("UDP Port", self.port_spin)

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
            "template": self.template_combo.currentData(),
            "name": self.name_edit.text().strip(),
            "instance": self.instance_spin.value(),
            "port": self.port_spin.value(),
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
