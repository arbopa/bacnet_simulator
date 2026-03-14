from __future__ import annotations

import json

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.object_model import BehaviorMode, ObjectModel, ObjectType


_RESPONSE_PRESETS = {
    "custom": {"kind": "", "inputs": {}, "params": {}},
    "ahu_sat": {
        "kind": "ahu_sat",
        "inputs": {"heating_valve": "", "cooling_valve": "", "fan_status": ""},
        "params": {"base_temp": 58.0, "off_temp": 72.0, "heat_gain": 25.0, "cool_gain": 30.0, "tau": 20.0},
    },
    "mixed_air": {
        "kind": "mixed_air",
        "inputs": {"outdoor_temp": "", "return_temp": "", "damper_cmd": ""},
        "params": {"tau": 12.0},
    },
    "vav_flow": {
        "kind": "vav_flow",
        "inputs": {"damper_cmd": ""},
        "params": {"min_flow": 150.0, "max_flow": 900.0, "tau": 8.0},
    },
    "zone_temp": {
        "kind": "zone_temp",
        "inputs": {"flow": "", "supply_temp": "", "room_load": ""},
        "params": {"default_supply_temp": 55.0, "default_room_load": 0.2, "max_flow": 900.0, "k_air": 0.02, "k_load": 0.03},
    },
    "binary_status_delay": {
        "kind": "binary_status_delay",
        "inputs": {"command": ""},
        "params": {"rise_tau": 5.0, "fall_tau": 2.0},
    },
}


_DEFAULT_INPUT_POINTS = {
    "heating_valve": "HeatingValveCmd",
    "cooling_valve": "CoolingValveCmd",
    "fan_status": "SupplyFanStatus",
    "outdoor_temp": "OutdoorAirTemp",
    "return_temp": "ReturnAirTemp",
    "damper_cmd": "DamperCmd",
    "flow": "Flow",
    "supply_temp": "SupplyAirTemp",
    "room_load": "RoomLoad",
    "command": "SupplyFanCmd",
}


class ObjectEditor(QWidget):
    saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._object: ObjectModel | None = None
        self._applying_preset = False
        self._current_device_name: str = ""
        self._device_point_names: set[str] = set()

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
        self.out_of_service_check = QCheckBox("Out Of Service")
        self.cov_spin = QDoubleSpinBox()
        self.cov_spin.setRange(0.001, 1000.0)
        self.cov_spin.setValue(0.5)
        self.behavior_combo = QComboBox()
        self.behavior_combo.addItems([mode.value for mode in BehaviorMode])
        self.behavior_combo.currentIndexChanged.connect(self._apply_behavior_mode)

        self.linked_ref_edit = QLineEdit()
        self.schedule_ref_edit = QLineEdit()
        self.weekday_start_edit = QLineEdit()
        self.weekday_end_edit = QLineEdit()
        self.occ_spin = QDoubleSpinBox()
        self.occ_spin.setRange(-1_000_000, 1_000_000)
        self.unocc_spin = QDoubleSpinBox()
        self.unocc_spin.setRange(-1_000_000, 1_000_000)
        self.trend_source_edit = QLineEdit()

        self.response_preset_combo = QComboBox()
        self.response_preset_combo.addItem("Custom", "custom")
        self.response_preset_combo.addItem("AHU SAT", "ahu_sat")
        self.response_preset_combo.addItem("Mixed Air", "mixed_air")
        self.response_preset_combo.addItem("VAV Flow", "vav_flow")
        self.response_preset_combo.addItem("Zone Temp", "zone_temp")
        self.response_preset_combo.addItem("Binary Status Delay", "binary_status_delay")
        self.response_preset_combo.currentIndexChanged.connect(self._on_response_preset_changed)

        self.auto_map_btn = QPushButton("Auto-Map Inputs")
        self.auto_map_btn.clicked.connect(self._on_auto_map_inputs)

        self.response_kind_edit = QLineEdit()
        self.response_inputs_edit = QLineEdit()
        self.response_inputs_edit.setPlaceholderText('{"input_key": "Device.PointRef"}')
        self.response_params_edit = QLineEdit()
        self.response_params_edit.setPlaceholderText('{"tau": 20.0, "gain": 1.0}')
        self.missing_policy_combo = QComboBox()
        self.missing_policy_combo.addItems(["hold", "skip", "fallback"])
        self.fallback_spin = QDoubleSpinBox()
        self.fallback_spin.setRange(-1_000_000, 1_000_000)
        self.fallback_spin.setDecimals(3)
        self.max_rate_spin = QDoubleSpinBox()
        self.max_rate_spin.setRange(0.0, 1_000_000)
        self.max_rate_spin.setDecimals(3)

        form = QFormLayout()
        form.addRow("Object Name", self.name_edit)
        form.addRow("Type", self.type_combo)
        form.addRow("Units", self.units_edit)
        form.addRow("Description", self.description_edit)
        form.addRow("Present Value", self.value_spin)
        form.addRow("Initial Value", self.initial_spin)
        form.addRow("", self.writable_check)
        form.addRow("", self.out_of_service_check)
        form.addRow("COV Increment", self.cov_spin)
        form.addRow("Behavior", self.behavior_combo)
        form.addRow("Linked Point Ref", self.linked_ref_edit)
        form.addRow("Schedule Ref", self.schedule_ref_edit)
        form.addRow("Weekday Start", self.weekday_start_edit)
        form.addRow("Weekday End", self.weekday_end_edit)
        form.addRow("Occupied Value", self.occ_spin)
        form.addRow("Unoccupied Value", self.unocc_spin)
        form.addRow("Response Preset", self.response_preset_combo)
        form.addRow("Response Auto-Map", self.auto_map_btn)
        form.addRow("Response Kind", self.response_kind_edit)
        form.addRow("Response Inputs JSON", self.response_inputs_edit)
        form.addRow("Response Params JSON", self.response_params_edit)
        form.addRow("Missing Input Policy", self.missing_policy_combo)
        form.addRow("Fallback Value", self.fallback_spin)
        form.addRow("Max Rate / Sec", self.max_rate_spin)
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

    def set_device_context(self, device_name: str, point_names: list[str] | None = None) -> None:
        self._current_device_name = (device_name or "").strip()
        self._device_point_names = set(point_names or [])

    def _apply_behavior_mode(self) -> None:
        is_response = self.behavior_combo.currentText() == BehaviorMode.RESPONSE.value
        for widget in [
            self.response_preset_combo,
            self.auto_map_btn,
            self.response_kind_edit,
            self.response_inputs_edit,
            self.response_params_edit,
            self.missing_policy_combo,
            self.fallback_spin,
            self.max_rate_spin,
        ]:
            widget.setEnabled(self._object is not None and is_response)

    def _detect_response_preset_key(self, kind: str) -> str:
        k = (kind or "").strip().lower()
        return k if k in _RESPONSE_PRESETS else "custom"

    def _ref_for_current_device(self, point_name: str) -> str:
        if not self._current_device_name or not point_name:
            return ""
        if self._device_point_names and point_name not in self._device_point_names:
            return ""
        return f"{self._current_device_name}.{point_name}"

    def _autofill_inputs_for_preset(self, inputs_template: dict[str, str], existing_inputs: dict[str, str] | None = None) -> dict[str, str]:
        existing_inputs = existing_inputs or {}
        filled: dict[str, str] = {}
        for key in inputs_template.keys():
            existing = str(existing_inputs.get(key, "")).strip()
            if existing:
                filled[str(key)] = existing
                continue

            if key == "command":
                linked_ref = self.linked_ref_edit.text().strip()
                if linked_ref:
                    filled[str(key)] = linked_ref
                    continue

            default_point = _DEFAULT_INPUT_POINTS.get(key, "")
            filled[str(key)] = self._ref_for_current_device(default_point)
        return filled

    def _on_response_preset_changed(self) -> None:
        if self._applying_preset:
            return
        key = str(self.response_preset_combo.currentData() or "custom")
        if key == "custom":
            return
        preset = _RESPONSE_PRESETS.get(key, _RESPONSE_PRESETS["custom"])
        filled_inputs = self._autofill_inputs_for_preset(preset["inputs"], existing_inputs={})

        self._applying_preset = True
        try:
            self.response_kind_edit.setText(str(preset["kind"]))
            self.response_inputs_edit.setText(json.dumps(filled_inputs, separators=(",", ":")))
            self.response_params_edit.setText(json.dumps(preset["params"], separators=(",", ":")))
        finally:
            self._applying_preset = False

    def _on_auto_map_inputs(self) -> None:
        kind = self.response_kind_edit.text().strip().lower()
        preset = _RESPONSE_PRESETS.get(kind)
        if not preset:
            QMessageBox.information(self, "Auto-Map Inputs", "Select a known response preset/kind first.")
            return

        try:
            existing = self._parse_json_object(self.response_inputs_edit.text(), "Response Inputs")
        except ValueError as err:
            QMessageBox.warning(self, "Auto-Map Inputs", str(err))
            return

        merged = self._autofill_inputs_for_preset(preset["inputs"], existing_inputs={str(k): str(v) for k, v in existing.items()})
        self.response_inputs_edit.setText(json.dumps(merged, separators=(",", ":")))

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
            self.out_of_service_check,
            self.cov_spin,
            self.behavior_combo,
            self.linked_ref_edit,
            self.schedule_ref_edit,
            self.weekday_start_edit,
            self.weekday_end_edit,
            self.occ_spin,
            self.unocc_spin,
            self.trend_source_edit,
            self.response_preset_combo,
            self.auto_map_btn,
            self.response_kind_edit,
            self.response_inputs_edit,
            self.response_params_edit,
            self.missing_policy_combo,
            self.fallback_spin,
            self.max_rate_spin,
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
        self.out_of_service_check.setChecked(bool(obj.out_of_service))
        self.cov_spin.setValue(obj.cov_increment)
        self.behavior_combo.setCurrentText(obj.behavior.mode.value)
        self.linked_ref_edit.setText(obj.behavior.linked_point_ref)
        self.schedule_ref_edit.setText(obj.schedule.schedule_ref)
        self.weekday_start_edit.setText(obj.schedule.weekday_start)
        self.weekday_end_edit.setText(obj.schedule.weekday_end)
        self.occ_spin.setValue(obj.schedule.occupied_value)
        self.unocc_spin.setValue(obj.schedule.unoccupied_value)
        self.trend_source_edit.setText(str(obj.metadata.get("source_ref", "")))

        self.response_kind_edit.setText(obj.behavior.response_kind)
        self.response_inputs_edit.setText(json.dumps(obj.behavior.response_inputs, separators=(",", ":")))
        self.response_params_edit.setText(json.dumps(obj.behavior.response_params, separators=(",", ":")))
        self.missing_policy_combo.setCurrentText((obj.behavior.missing_input_policy or "hold").strip().lower())
        self.fallback_spin.setValue(float(obj.behavior.fallback_value))
        self.max_rate_spin.setValue(float(obj.behavior.max_rate_per_sec))

        preset_key = self._detect_response_preset_key(obj.behavior.response_kind)
        idx = self.response_preset_combo.findData(preset_key)
        if idx >= 0:
            self.response_preset_combo.setCurrentIndex(idx)

        self._apply_behavior_mode()

    def _parse_json_object(self, raw: str, field_name: str) -> dict:
        text = raw.strip()
        if not text:
            return {}
        try:
            value = json.loads(text)
        except Exception as err:
            raise ValueError(f"{field_name} is not valid JSON: {err}") from err
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be a JSON object")
        return value

    def _save(self) -> None:
        if not self._object:
            return

        try:
            inputs_obj = self._parse_json_object(self.response_inputs_edit.text(), "Response Inputs")
            params_obj = self._parse_json_object(self.response_params_edit.text(), "Response Params")
        except ValueError as err:
            QMessageBox.warning(self, "Object Save", str(err))
            return

        self._object.name = self.name_edit.text().strip()
        self._object.object_type = ObjectType(self.type_combo.currentText())
        self._object.units = self.units_edit.text().strip()
        self._object.description = self.description_edit.text().strip()
        self._object.present_value = self.value_spin.value()
        self._object.initial_value = self.initial_spin.value()
        self._object.writable = self.writable_check.isChecked()
        self._object.out_of_service = self.out_of_service_check.isChecked()
        self._object.cov_increment = self.cov_spin.value()
        self._object.behavior.mode = BehaviorMode(self.behavior_combo.currentText())
        self._object.behavior.linked_point_ref = self.linked_ref_edit.text().strip()
        self._object.schedule.schedule_ref = self.schedule_ref_edit.text().strip()
        self._object.schedule.weekday_start = self.weekday_start_edit.text().strip() or "06:00"
        self._object.schedule.weekday_end = self.weekday_end_edit.text().strip() or "18:00"
        self._object.schedule.occupied_value = self.occ_spin.value()
        self._object.schedule.unoccupied_value = self.unocc_spin.value()

        self._object.behavior.response_kind = self.response_kind_edit.text().strip()
        self._object.behavior.response_inputs = {str(k): str(v) for k, v in inputs_obj.items()}

        parsed_params: dict[str, float] = {}
        for key, value in params_obj.items():
            try:
                parsed_params[str(key)] = float(value)
            except (TypeError, ValueError):
                QMessageBox.warning(self, "Object Save", f"Response param '{key}' must be numeric")
                return
        self._object.behavior.response_params = parsed_params
        self._object.behavior.missing_input_policy = self.missing_policy_combo.currentText().strip().lower()
        self._object.behavior.fallback_value = self.fallback_spin.value()
        self._object.behavior.max_rate_per_sec = self.max_rate_spin.value()

        trend_source = self.trend_source_edit.text().strip()
        if trend_source:
            self._object.metadata["source_ref"] = trend_source
        elif "source_ref" in self._object.metadata:
            self._object.metadata.pop("source_ref", None)

        self.saved.emit()
