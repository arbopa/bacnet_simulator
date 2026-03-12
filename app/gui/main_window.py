from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.gui.device_editor import DeviceEditor
from app.gui.log_panel import LogPanel
from app.gui.object_editor import ObjectEditor
from app.gui.project_tree import ProjectTree
from app.gui.trend_view import TrendView
from app.models.project_model import ProjectModel


class MainWindow(QMainWindow):
    new_project_requested = Signal()
    open_project_requested = Signal()
    save_project_requested = Signal()
    save_as_project_requested = Signal()
    start_sim_requested = Signal()
    stop_sim_requested = Signal()
    pause_sim_requested = Signal()
    resume_sim_requested = Signal()
    reset_sim_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BACnet BAS Simulator")
        self.resize(1600, 980)

        self.project_tree = ProjectTree()
        self.device_editor = DeviceEditor()
        self.object_editor = ObjectEditor()
        self.live_table = QTableWidget(0, 4)
        self.live_table.setHorizontalHeaderLabels(["Point", "Value", "Writable", "Behavior"])
        self.trend_view = TrendView()
        self.log_panel = LogPanel()
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self._build_toolbar()
        self._build_layout()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        toolbar.addAction("New", self.new_project_requested.emit)
        toolbar.addAction("Open", self.open_project_requested.emit)
        toolbar.addAction("Save", self.save_project_requested.emit)
        toolbar.addAction("Save As", self.save_as_project_requested.emit)
        toolbar.addSeparator()
        toolbar.addAction("Start", self.start_sim_requested.emit)
        toolbar.addAction("Stop", self.stop_sim_requested.emit)
        toolbar.addAction("Pause", self.pause_sim_requested.emit)
        toolbar.addAction("Resume", self.resume_sim_requested.emit)
        toolbar.addAction("Reset", self.reset_sim_requested.emit)

    def _build_layout(self) -> None:
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(self.project_tree)

        editor_panel = QWidget()
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.addWidget(self.device_editor)
        editor_layout.addWidget(self.object_editor)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Live Values"))
        right_layout.addWidget(self.live_table)
        right_layout.addWidget(QLabel("Trend"))
        right_layout.addWidget(self.trend_view)

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(left_panel)
        top_splitter.addWidget(editor_panel)
        top_splitter.addWidget(right_panel)
        top_splitter.setStretchFactor(0, 2)
        top_splitter.setStretchFactor(1, 3)
        top_splitter.setStretchFactor(2, 4)

        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.addWidget(QLabel("Event Log / BACnet Activity"))
        bottom_layout.addWidget(self.log_panel)

        root_splitter = QSplitter(Qt.Orientation.Vertical)
        root_splitter.addWidget(top_splitter)
        root_splitter.addWidget(bottom_panel)
        root_splitter.setStretchFactor(0, 4)
        root_splitter.setStretchFactor(1, 1)

        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.addWidget(root_splitter)
        self.setCentralWidget(container)

    def set_project(self, project: ProjectModel) -> None:
        self.project_tree.populate(project)
        self.rebuild_live_table(project)
        self.status.showMessage(f"Loaded project: {project.name}")

    def rebuild_live_table(self, project: ProjectModel) -> None:
        rows = sum(len(device.objects) for device in project.devices)
        self.live_table.setRowCount(rows)
        row = 0
        for device in project.devices:
            for point in device.objects:
                ref = f"{device.name}.{point.name}"
                self.live_table.setItem(row, 0, QTableWidgetItem(ref))
                self.live_table.setItem(row, 1, QTableWidgetItem(str(point.present_value)))
                self.live_table.setItem(row, 2, QTableWidgetItem("Yes" if point.writable else "No"))
                self.live_table.setItem(row, 3, QTableWidgetItem(point.behavior.mode.value))
                row += 1

    def update_live_values(self, snapshot: dict[str, float]) -> None:
        for row in range(self.live_table.rowCount()):
            ref_item = self.live_table.item(row, 0)
            if not ref_item:
                continue
            ref = ref_item.text()
            if ref in snapshot:
                value_item = self.live_table.item(row, 1)
                if value_item:
                    value_item.setText(f"{snapshot[ref]:.3f}")

    def selected_point_ref(self) -> Optional[str]:
        indexes = self.live_table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        ref_item = self.live_table.item(row, 0)
        return ref_item.text() if ref_item else None

    def select_live_point(self, point_ref: str) -> None:
        for row in range(self.live_table.rowCount()):
            ref_item = self.live_table.item(row, 0)
            if ref_item and ref_item.text() == point_ref:
                self.live_table.selectRow(row)
                return

    def log(self, message: str) -> None:
        self.log_panel.append_line(message)
        self.status.showMessage(message, 3000)
