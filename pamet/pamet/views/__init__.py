from PySide6.QtWidgets import QApplication
from pamet.views.tab.widget import TabWidget


def current_window():
    return QApplication.activeWindow()


def current_tab() -> TabWidget:
    return current_window().current_tab()
