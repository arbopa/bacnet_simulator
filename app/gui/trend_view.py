from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget


class TrendView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.series = QLineSeries()
        self.chart = QChart()
        self.chart.legend().hide()
        self.chart.addSeries(self.series)

        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("Seconds")
        self.axis_x.setLabelFormat("%.0f")

        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("Value")
        self.axis_y.setLabelFormat("%.1f")

        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(self.chart_view.renderHints())

        layout = QVBoxLayout(self)
        layout.addWidget(self.chart_view)

    def set_title(self, title: str) -> None:
        self.chart.setTitle(title)

    def update_samples(self, samples: list[tuple[float, float]]) -> None:
        self.series.clear()
        if not samples:
            return
        t0 = samples[0][0]
        min_v = min(v for _, v in samples)
        max_v = max(v for _, v in samples)
        for ts, val in samples:
            self.series.append(ts - t0, val)

        duration = max(1.0, samples[-1][0] - t0)
        self.axis_x.setRange(0.0, duration)
        if abs(max_v - min_v) < 0.01:
            min_v -= 1.0
            max_v += 1.0
        self.axis_y.setRange(min_v, max_v)
