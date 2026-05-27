"""Python backend (controller) for the QML-based AppWindow.

Thin routing layer: translates QML @Slot calls into @action calls.
State lives in AppWindowViewState; mutation logic lives in
app_window_actions.
"""

import json
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import Property, QEvent, QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication, QKeyEvent, QWindow
from PySide6.QtWidgets import QFileDialog

from pamet.actions.app import (
    close_current_tab,
    close_tab,
    next_tab,
    open_tab,
    previous_tab,
    restore_tab,
    switch_to_tab,
    update_nav_state,
    update_tab_title,
    update_tab_url,
)
from pamet.services.rest_api.desktop_access_token import DESKTOP_ACCESS_TOKEN
from pamet.views.app_window.view_state import AppWindowViewState

# ── Title bar double-click event filter ──────────────────────────────


class TitleBarDoubleClickFilter(QObject):
    """Intercepts double-clicks in the title-bar region of a QQuickWindow
    and toggles maximize/restore.  Installed as a native event filter
    because QML TapHandler passive grabs don't reliably fire
    onDoubleTapped over Controls like TabBar."""

    def __init__(self, window: QWindow, title_bar_height: int = 40):
        super().__init__(window)
        self._window = window
        self._title_bar_height = title_bar_height

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Type.MouseButtonDblClick
            and event.button() == Qt.MouseButton.LeftButton
            and event.position().y() < self._title_bar_height
        ):
            if self._window.visibility() == QWindow.Visibility.Maximized:
                self._window.showNormal()
            else:
                self._window.showMaximized()
            return True
        return False


# ── Backend QObject exposed to QML ──────────────────────────────────


class QmlAppBackend(QObject):
    """Controller that QML binds to.  Routes slot calls to @action functions.

    State is read from the separate AppWindowViewState object (also
    exposed to QML as ``state``).  This object only holds the
    injection script and URL-classification helpers.
    """

    devToolsVisibleChanged = Signal()

    def __init__(
        self,
        view_state: AppWindowViewState,
        endpoint: str,
        desktop_api_base_url: str,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._state = view_state
        self._dev_tools_visible = False
        self._endpoint = endpoint

        # Collect internal hosts for URL classification
        self._internal_hosts: set[str] = set()
        for url_str in (endpoint, desktop_api_base_url):
            if url_str:
                host = urlparse(url_str).hostname
                if host:
                    self._internal_hosts.add(host)

        # Build the injection script source
        token_json = json.dumps(DESKTOP_ACCESS_TOKEN or "")
        api_base_url_json = json.dumps(desktop_api_base_url or "")
        self._injection_script = (
            f"window.PAMET_DESKTOP_ACCESS_TOKEN = {token_json};\n"
            f"window.PAMET_DESKTOP_API_BASE_URL = {api_base_url_json};\n"
            "console.log('Desktop access token injected');\n"
        )

    # -- Properties --

    @Property(str, constant=True)
    def injectionScript(self) -> str:
        return self._injection_script

    # -- Slots that route to @action functions --

    @Slot(str, bool)
    def openTab(self, url: str, switch_to: bool = True) -> None:
        open_tab(self._state, url, switch_to)

    @Slot(int)
    def closeTab(self, index: int) -> None:
        close_tab(self._state, index)

    @Slot()
    def closeCurrentTab(self) -> None:
        close_current_tab(self._state)

    @Slot(int, str)
    def updateTabTitle(self, index: int, title: str) -> None:
        update_tab_title(self._state, index, title)

    @Slot(int, str)
    def updateTabUrl(self, index: int, url: str) -> None:
        update_tab_url(self._state, index, url)

    @Slot(bool, bool)
    def updateNavState(self, can_back: bool, can_forward: bool) -> None:
        update_nav_state(self._state, can_back, can_forward)

    @Slot()
    def nextTab(self) -> None:
        next_tab(self._state)

    @Slot()
    def previousTab(self) -> None:
        previous_tab(self._state)

    @Slot(int)
    def switchToTab(self, index: int) -> None:
        switch_to_tab(self._state, index)

    @Slot()
    def openNewTab(self) -> None:
        open_tab(self._state, self._endpoint, switch_to=True)

    @Slot()
    def restoreTab(self) -> None:
        restore_tab(self._state)

    # -- Non-action helpers (pure side-effects, no state mutation) --

    @Slot(str, result=bool)
    def isInternalUrl(self, url: str) -> bool:
        """Return True if *url* points to one of the known internal hosts."""
        parsed = urlparse(url)
        scheme = parsed.scheme
        if scheme in ("data", "blob", "javascript", "about", ""):
            return True
        host = parsed.hostname or ""
        return host in self._internal_hosts

    @Slot(str)
    def openInSystemBrowser(self, url: str) -> None:
        print(f"Opening external URL in system browser: {url}")
        QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def toggleShell(self) -> None:
        window = QGuiApplication.focusWindow()
        if window is None:
            return
        for etype in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            event = QKeyEvent(
                etype, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier
            )
            QGuiApplication.sendEvent(window, event)

    @Slot()
    def toggleDevTools(self) -> None:
        self._dev_tools_visible = not self._dev_tools_visible
        self.devToolsVisibleChanged.emit()

    @Property(bool, notify=devToolsVisibleChanged)
    def devToolsVisible(self) -> bool:
        return self._dev_tools_visible

    @Slot(QObject)
    def handleDownload(self, download: QObject) -> None:
        suggested = download.property("suggestedFileName") or "download"
        default_dir = Path.home() / "Downloads"
        default_path = str(default_dir / suggested)

        path, _ = QFileDialog.getSaveFileName(
            None, "Save download", default_path, "All files (*)"
        )
        if not path:
            download.cancel()
            return

        dest = Path(path)
        download.setProperty("downloadDirectory", str(dest.parent))
        download.setProperty("downloadFileName", dest.name)
        download.accept()
