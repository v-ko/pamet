from __future__ import annotations
from PySide6.QtWidgets import QApplication


def current_window() -> WindowWidget:
    return QApplication.activeWindow()


def current_tab() -> TabWidget:
    return current_window().current_tab()
