from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit


class LogPanel(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def append_line(self, message: str) -> None:
        self.appendPlainText(message)
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
