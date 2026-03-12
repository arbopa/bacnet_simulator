from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.object_model import BehaviorMode, ObjectModel, ObjectType


class ObjectEditor(QWidget):
    saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._object: ObjectModel | None = None

        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems([item.value for item in ObjectType])
        self.units_edit = QLineEdit()
        self.description_edit = QLineEdit()
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1_000_000, 1_000_000)
        self.value_spin.setDecimals(3)
        self.initial_spin = QDoubleSpinBox()
        self.initial_spin.setRange(-1_000_000, 1_000_000)
        self.initial_spin.setDecimals(3)
        self.writable_check = QCheckBox("Writable")
        self.cov_spin = QDoubleSpinBox()
        self.cov_spin.setRange(0.001, 1000.0)
        self.cov_spin.setValue(0.5)
        self.behavior_combo = QComboBox()
        self.behavior_combo.addItems([mode.value for mode in BehaviorMode])

        self.linked_ref_edit = QLineEdit()
        self.schedule_ref_edit = QLineEdit()
        self.weekday_start_edit = QLineEdit()
        self.weekday_end_edit = QLineEdit()
        self.occ_spin = QDoubleSpinBox()
        self.occ_spin.setRange(-1_000_000, 1_000_000)
        self.unocc_spin = QDoubleSpinBox()
        self.unocc_spin.setRange(-1_000_000, 1_000_000)
        self.trend_source_edit = QLineEdit()

        form = QFormLayout()
        form.addRow("Object Name", self.name_edit)
        form.addRow("Type", self.type_combo)
        form.addRow("Units", self.units_edit)
        form.addRow("Description", self.description_edit)
        form.addRow("Present Value", self.value_spin)
        form.addRow("Initial Value", self.initial_spin)
        form.addRow("", self.writable_check)
        form.addRow("COV Increment", self.cov_spin)
        form.addRow("Behavior", self.behavior_combo)
        form.addRow("Linked Point Ref", self.linked_ref_edit)
        form.addRow("Schedule Ref", self.schedule_ref_edit)
        form.addRow("Weekday Start", self.weekday_start_edit)
        form.addRow("Weekday End", self.weekday_end_edit)
        form.addRow("Occupied Value", self.occ_spin)
        form.addRow("Unoccupied Value", self.unocc_spin)
        form.addRow("Trend Source Ref", self.trend_source_edit)

        save_btn = QPushButton("Save Object")
        save_btn.clicked.connect(self._save)

        box = QGroupBox("Object Editor")
        box.setLayout(form)

        layout = QVBoxLayout(self)
        layout.addWidget(box)
        row = QHBoxLayout()
        row.addWidget(save_btn)
        row.addStretch(1)
        layout.addLayout(row)

    def set_object(self, obj: ObjectModel | None) -> None:
        self._object = obj
        enabled = obj is not None
        for widget in [
            self.name_edit,
            self.type_combo,
            self.units_edit,
            self.description_edit,
            self.value_spin,
            self.initial_spin,
            self.writable_check,
            self.cov_spin,
            self.behavior_combo,
            self.linked_ref_edit,
            self.schedule_ref_edit,
            self.weekday_start_edit,
            self.weekday_end_edit,
            self.occ_spin,
            self.unocc_spin,
            self.trend_source_edit,
        ]:
            widget.setEnabled(enabled)
        if obj is None:
            self.name_edit.setText("")
            return

        self.name_edit.setText(obj.name)
        self.type_combo.setCurrentText(obj.object_type.value)
        self.units_edit.setText(obj.units)
        self.description_edit.setText(obj.description)
        try:
            self.value_spin.setValue(float(obj.present_value))
            self.initial_spin.setValue(float(obj.initial_value))
        except (TypeError, ValueError):
            self.value_spin.setValue(0.0)
            self.initial_spin.setValue(0.0)
        self.writable_check.setChecked(obj.writable)
        self.cov_spin.setValue(obj.cov_increment)
        self.behavior_combo.setCurrentText(obj.behavior.mode.value)
        self.linked_ref_edit.setText(obj.behavior.linked_point_ref)
        self.schedule_ref_edit.setText(obj.schedule.schedule_ref)
        self.weekday_start_edit.setText(obj.schedule.weekday_start)
        self.weekday_end_edit.setText(obj.schedule.weekday_end)
        self.occ_spin.setValue(obj.schedule.occupied_value)
        self.unocc_spin.setValue(obj.schedule.unoccupied_value)
        self.trend_source_edit.setText(str(obj.metadata.get("source_ref", "")))

    def _save(self) -> None:
        if not self._object:
            return
        self._object.name = self.name_edit.text().strip()
        self._object.object_type = ObjectType(self.type_combo.currentText())
        self._object.units = self.units_edit.text().strip()
        self._object.description = self.description_edit.text().strip()
        self._object.present_value = self.value_spin.value()
        self._object.initial_value = self.initial_spin.value()
        self._object.writable = self.writable_check.isChecked()
        self._object.cov_increment = self.cov_spin.value()
        self._object.behavior.mode = BehaviorMode(self.behavior_combo.currentText())
        self._object.behavior.linked_point_ref = self.linked_ref_edit.text().strip()
        self._object.schedule.schedule_ref = self.schedule_ref_edit.text().strip()
        self._object.schedule.weekday_start = self.weekday_start_edit.text().strip() or "06:00"
        self._object.schedule.weekday_end = self.weekday_end_edit.text().strip() or "18:00"
        self._object.schedule.occupied_value = self.occ_spin.value()
        self._object.schedule.unoccupied_value = self.unocc_spin.value()

        trend_source = self.trend_source_edit.text().strip()
        if trend_source:
            self._object.metadata["source_ref"] = trend_source
        elif "source_ref" in self._object.metadata:
            self._object.metadata.pop("source_ref", None)

        self.saved.emit()
