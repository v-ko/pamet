from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

import pamet
from fusion.libs.command import command
from pamet import desktop_app
from pamet.actions import tab as tab_actions
from pamet.actions import window as window_actions
from pamet.desktop_app.config import repo_settings_path
from pamet.desktop_app.screen_snippet import grab_screen_snippet as _grab_screen_snippet
from pamet.desktop_app.util import current_tab, current_window


@command(title="Show all commands")
def open_command_palette():
    window_actions.open_command_view(current_window().state(), prefix=">")


@command(title="Go to file")
def open_command_palette_go_to_file():
    window_actions.open_command_view(current_window().state())


@command(title="Close tab")
def close_current_tab():
    window = current_window()
    tab = window.current_tab()
    window_actions.close_tab(window.state(), tab.state())


@command(title="Navigate back")
def navigate_back():
    tab = current_tab()
    tab_actions.navigation_back(tab.state())


@command(title="Navigate forward")
def navigate_forward():
    tab = current_tab()
    tab_actions.navigation_forward(tab.state())


@command(title="Toggle between last two pages")
def toggle_between_last_two_pages():
    tab = current_tab()
    tab_actions.navigation_toggle_last(tab.state())


@command(title="Open user settings (JSON)")
def open_user_settings_json():
    settings_path = desktop_app.user_settings_path()
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(settings_path)))


@command(title="Grab screen snippet")
def grab_screen_snippet():
    _grab_screen_snippet()
