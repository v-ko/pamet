from __future__ import annotations

from PySide6.QtCore import Qt

from pamet.desktop_app.app import DesktopApp


def grab_screen_snippet():
    """
    Show the selector widget for grabbing a screenshot snippet.

    Kept as a standalone desktop utility so it can be ported to another app
    without digging through command/legacy modules.
    """
    app = DesktopApp.instance()
    if not app:
        return

    active_window = app.activeWindow()
    if not active_window:
        # Minimize non-active windows to avoid selecting them in snippets.
        for window in app.topLevelWidgets():
            if window != active_window:
                window.setWindowState(Qt.WindowMinimized)

    selector = getattr(app, "selector_widget", None)
    if selector:
        selector.showFullScreen()
