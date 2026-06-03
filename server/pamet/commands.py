from __future__ import annotations

from typing import cast

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QWindow
from sivkit.libs.command import command

import pamet
from pamet import desktop_app
from pamet.desktop_app.app import DesktopApp


@command(title="Open user settings (JSON)")
def open_user_settings_json():
    settings_path = desktop_app.user_settings_path()
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(settings_path)))


@command(title="Grab screen snippet")
def grab_screen_snippet():
    app = cast(DesktopApp, DesktopApp.instance())
    if not app:
        return

    active_window = app.activeWindow()
    if not active_window:
        for window in app.topLevelWidgets():
            if window != active_window:
                window.setWindowState(Qt.WindowState.WindowMinimized)

    app.selector_widget.showFullScreen()


@command(title="Raise window")
def raise_window():
    app = cast(DesktopApp, DesktopApp.instance())
    if not app:
        return
    # Works for both QML (QQuickWindow) and widgets (QWidget windows)
    windows = app.allWindows()
    if windows:
        win = windows[0]
        if win.visibility() == win.Visibility.Minimized:
            win.showNormal()
        win.requestActivate()
        win.raise_()


@command(title="Open backups folder")
def open_backups_folder(project_id: str):
    dss = pamet.desktop_storage_service()
    pfm = dss.project_folder_manager(project_id)
    backup_folder = pfm.backup_service.backup_folder
    backup_folder.mkdir(parents=True, exist_ok=True)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(backup_folder)))
