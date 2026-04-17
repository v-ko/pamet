import json
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtGui import (
    QCursor,
    QDesktopServices,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPalette,
    QShortcut,
)
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from pamet.desktop_app.web_shell_actions import close_tab
from pamet.desktop_app.web_shell_view_state import TabState, WebShellViewState
from pamet.services.rest_api.auth import DESKTOP_ACCESS_TOKEN

_RESIZE_GRIP = 5  # px – edge/corner resize zone for frameless window


class PametWebEnginePage(QWebEnginePage):
    """Custom page that forwards all JS console messages (including info) to stdout."""

    def __init__(self, profile, parent=None, internal_hosts: set[str] | None = None):
        super().__init__(profile, parent)
        self._internal_hosts: set[str] = internal_hosts or set()

    def _is_internal_url(self, url: QUrl) -> bool:
        """Return True if *url* points to one of the known internal hosts."""
        host = url.host()
        return host in self._internal_hosts

    def javaScriptConsoleMessage(self, level, message, line, source_id):
        tag = {
            QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: "js:info",
            QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "js:warn",
            QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: "js:error",
        }.get(level, "js")
        print(f"{tag}: {message}")

    def acceptNavigationRequest(
        self, url: QUrl | str, nav_type, is_main_frame: bool
    ) -> bool:
        """Block external navigations and open them in the system browser."""
        if isinstance(url, str):
            url = QUrl(url)
        if not is_main_frame:
            return True
        if url.scheme() in ("data", "blob", "javascript", "about"):
            return True
        if self._is_internal_url(url):
            return True
        # External URL – open in default browser and reject the navigation
        print(f"Opening external URL in system browser: {url.toString()}")
        QDesktopServices.openUrl(url)
        return False

    def createWindow(self, window_type):
        """Handle middle-click / ctrl+click link opens as new tabs."""
        print(f"createWindow called with type: {window_type}")
        window = self.parent().window()
        if isinstance(window, WebShellWindow):
            new_view = window.open_tab("", switch_to=False)
            return new_view.page()
        return super().createWindow(window_type)


class WebShellWindow(QWidget):

    def __init__(
        self,
        endpoint: str,
        desktop_api_base_url: str,
        webengine_profile_root: Path,
        show_dev_tools: bool = False,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

        self.desktop_access_token = DESKTOP_ACCESS_TOKEN
        self.desktop_api_base_url = desktop_api_base_url
        self.show_dev_tools = show_dev_tools
        self._endpoint_base = endpoint  # Used to build URLs for new tabs

        # Collect all hosts that should be treated as internal
        self._internal_hosts: set[str] = set()
        for url_str in (endpoint, desktop_api_base_url):
            if url_str:
                host = QUrl(url_str).host()
                if host:
                    self._internal_hosts.add(host)

        # Web engine profile (shared across all tabs)
        profile_root = Path(webengine_profile_root)
        profile_root.mkdir(parents=True, exist_ok=True)
        self.web_profile = QWebEngineProfile("pamet-desktop", self)
        self.web_profile.setPersistentStoragePath(str(profile_root / "storage"))

        # --- View State ---
        self.state = WebShellViewState(parent=self)

        # --- Build UI ---
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            _RESIZE_GRIP, _RESIZE_GRIP, _RESIZE_GRIP, _RESIZE_GRIP
        )
        root_layout.setSpacing(0)

        # Top bar: back, toggle, forward, tab bar, window buttons
        self.title_bar = _TitleBarWidget(self)
        top_bar = QHBoxLayout(self.title_bar)
        top_bar.setContentsMargins(4, 2, 4, 2)
        top_bar.setSpacing(2)

        self.back_button = QPushButton("\u25c0")
        self.back_button.setFixedSize(28, 28)
        self.back_button.setToolTip("Back")
        self.toggle_button = QPushButton("\u21c4")
        self.toggle_button.setFixedSize(28, 28)
        self.toggle_button.setToolTip("Toggle desktop/web shell")
        self.forward_button = QPushButton("\u25b6")
        self.forward_button.setFixedSize(28, 28)
        self.forward_button.setToolTip("Forward")

        self.tab_bar = QTabBar()
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setMovable(True)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDrawBase(False)

        # Window control buttons
        self.minimize_button = QPushButton("\u2014")
        self.minimize_button.setFixedSize(28, 28)
        self.maximize_button = QPushButton("\u25a1")
        self.maximize_button.setFixedSize(28, 28)
        self.close_button = QPushButton("\u2715")
        self.close_button.setFixedSize(28, 28)

        self._apply_title_bar_style()

        top_bar.addWidget(self.back_button)
        top_bar.addWidget(self.toggle_button)
        top_bar.addWidget(self.forward_button)
        top_bar.addWidget(self.tab_bar, 1)
        top_bar.addItem(
            QSpacerItem(40, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        )
        top_bar.addWidget(self.minimize_button)
        top_bar.addWidget(self.maximize_button)
        top_bar.addWidget(self.close_button)

        root_layout.addWidget(self.title_bar)

        # Stacked widget holding one QWebEngineView per tab
        self.content_area = QSplitter()
        self.content_area.setOrientation(Qt.Orientation.Vertical)
        self.stack = QStackedWidget()
        self.content_area.addWidget(self.stack)
        root_layout.addWidget(self.content_area, 1)

        # Dev tools (shared inspector)
        self.dev_tools_view: QWebEngineView | None = None
        if show_dev_tools:
            self.dev_tools_view = QWebEngineView()
            self.content_area.addWidget(self.dev_tools_view)
            # Give dev tools a reasonable initial height
            self.content_area.setSizes([400, 200])
            self.dev_tools_view.hide()

        self.resize(800, 600)

        # --- Connections (widget -> state) ---
        self.tab_bar.currentChanged.connect(self._on_tab_bar_changed)
        self.tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
        self.tab_bar.installEventFilter(self)
        self.back_button.clicked.connect(self._navigate_back)
        self.forward_button.clicked.connect(self._navigate_forward)
        self.toggle_button.clicked.connect(self._toggle_shell)
        self.minimize_button.clicked.connect(self.showMinimized)
        self.maximize_button.clicked.connect(self._toggle_maximize)
        self.close_button.clicked.connect(self.close)

        # --- Connections (state -> widget) ---
        self.state.title_changed.connect(self.setWindowTitle)
        self.state.tabs_changed.connect(self._sync_tab_bar)
        self.state.current_tab_index_changed.connect(self._on_state_tab_switched)

        # --- Shortcuts ---
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_current_tab)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self._toggle_dev_tools)
        for i in range(1, 10):
            QShortcut(
                QKeySequence(f"Ctrl+{i}"),
                self,
                lambda idx=i - 1: (
                    self.state.__setattr__("current_tab_index", idx)
                    if idx < len(self.state.tabs)
                    else None
                ),
            )

        # --- Open the initial tab ---
        self.state.title = "Pamet"
        self.open_tab(endpoint)
        self.show()

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    def open_tab(self, url: str, switch_to: bool = True) -> QWebEngineView:
        """Create a new tab with its own QWebEngineView, load *url*."""
        tab_id = uuid4().hex[:8]
        web_view = QWebEngineView()
        page = PametWebEnginePage(
            self.web_profile,
            web_view,
            internal_hosts=self._internal_hosts,
        )
        web_view.setPage(page)
        self._inject_desktop_config(web_view)
        web_view.loadFinished.connect(self._handle_load_finished)
        web_view.titleChanged.connect(
            lambda title, wv=web_view: self._on_web_title_changed(wv, title)
        )

        self.stack.addWidget(web_view)
        tab_state = TabState(tab_id=tab_id, url=url)
        self.state.add_tab(tab_state, switch_to=switch_to)

        if url:
            web_view.load(QUrl(url))

        # Attach dev tools to first tab initially
        if self.dev_tools_view and self.stack.count() == 1:
            web_view.page().setDevToolsPage(self.dev_tools_view.page())

        return web_view

    def _current_web_view(self) -> QWebEngineView | None:
        w = self.stack.currentWidget()
        return w if isinstance(w, QWebEngineView) else None

    # ------------------------------------------------------------------
    # Widget -> State
    # ------------------------------------------------------------------

    def _on_tab_bar_changed(self, index: int):
        if index < 0:
            return
        self.state.current_tab_index = index

    def _on_tab_close_requested(self, index: int):
        if len(self.state.tabs) <= 1:
            self.close()
            return
        close_tab(self.state, index)
        widget = self.stack.widget(index)
        self.stack.removeWidget(widget)
        widget.deleteLater()

    def eventFilter(self, obj, event):
        """Middle-click close and left-drag/double-click on empty tab-bar area."""
        if obj is self.tab_bar:
            if event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.MiddleButton:
                    index = self.tab_bar.tabAt(event.pos())
                    if index >= 0:
                        self._on_tab_close_requested(index)
                        return True
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    if self.tab_bar.tabAt(event.pos()) < 0:
                        self.windowHandle().startSystemMove()
                        return True
            if event.type() == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    if self.tab_bar.tabAt(event.pos()) < 0:
                        self._toggle_maximize()
                        return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # State -> Widget
    # ------------------------------------------------------------------

    def _sync_tab_bar(self):
        """Rebuild tab-bar labels from state."""
        self.tab_bar.blockSignals(True)
        while self.tab_bar.count() > len(self.state.tabs):
            self.tab_bar.removeTab(self.tab_bar.count() - 1)
        while self.tab_bar.count() < len(self.state.tabs):
            self.tab_bar.addTab("")
        for i, ts in enumerate(self.state.tabs):
            self.tab_bar.setTabText(i, ts.title or "Untitled")
        self.tab_bar.blockSignals(False)

    def _on_state_tab_switched(self, index: int):
        if index < 0:
            return
        self.tab_bar.blockSignals(True)
        self.tab_bar.setCurrentIndex(index)
        self.tab_bar.blockSignals(False)
        self.stack.setCurrentIndex(index)

        # Rebind dev tools to the active tab
        if self.dev_tools_view:
            wv = self._current_web_view()
            if wv:
                wv.page().setDevToolsPage(self.dev_tools_view.page())

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _navigate_back(self):
        wv = self._current_web_view()
        if wv:
            wv.back()

    def _navigate_forward(self):
        wv = self._current_web_view()
        if wv:
            wv.forward()

    # ------------------------------------------------------------------
    # Web view callbacks
    # ------------------------------------------------------------------

    def _on_web_title_changed(self, web_view: QWebEngineView, title: str):
        index = self.stack.indexOf(web_view)
        if index >= 0:
            self.state.update_tab_title(index, title)
            # Update window title to current tab
            if index == self.state.current_tab_index:
                self.state.title = f"Pamet — {title}" if title else "Pamet"

    def _handle_load_finished(self, ok):
        if ok:
            print("Page loaded successfully.")
        else:
            print(
                "Failed to load page. Maybe you're debugging and the frontend server is not started?"
            )

    # ------------------------------------------------------------------
    # Toggle shell
    # ------------------------------------------------------------------

    def _toggle_shell(self):
        wv = self._current_web_view()
        if wv:
            press = QKeyEvent(
                QEvent.Type.KeyPress,
                Qt.Key.Key_Backspace,
                Qt.KeyboardModifier.NoModifier,
            )
            release = QKeyEvent(
                QEvent.Type.KeyRelease,
                Qt.Key.Key_Backspace,
                Qt.KeyboardModifier.NoModifier,
            )
            wv.focusProxy().event(press)
            wv.focusProxy().event(release)

    # ------------------------------------------------------------------
    # Dev tools toggle
    # ------------------------------------------------------------------

    def _toggle_dev_tools(self):
        if not self.dev_tools_view:
            self.dev_tools_view = QWebEngineView()
            self.content_area.addWidget(self.dev_tools_view)
            wv = self._current_web_view()
            if wv:
                wv.page().setDevToolsPage(self.dev_tools_view.page())
            self.dev_tools_view.show()
            return

        if self.dev_tools_view.isVisible():
            self.dev_tools_view.hide()
        else:
            wv = self._current_web_view()
            if wv:
                wv.page().setDevToolsPage(self.dev_tools_view.page())
            self.dev_tools_view.show()
            # Ensure dev tools get a reasonable portion of space
            total = self.content_area.height()
            if total > 0:
                self.content_area.setSizes([total * 2 // 3, total // 3])

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    def _close_current_tab(self):
        idx = self.state.current_tab_index
        if idx >= 0:
            self._on_tab_close_requested(idx)

    # ------------------------------------------------------------------
    # Config injection
    # ------------------------------------------------------------------

    def _inject_desktop_config(self, web_view: QWebEngineView):
        """Inject desktop access token into the web view."""
        token_json = json.dumps(self.desktop_access_token or "")
        api_base_url_json = json.dumps(self.desktop_api_base_url or "")
        script_code = f"""
        window.PAMET_DESKTOP_ACCESS_TOKEN = {token_json};
        window.PAMET_DESKTOP_API_BASE_URL = {api_base_url_json};
        console.log('Desktop access token injected');
        """

        script = QWebEngineScript()
        script.setSourceCode(script_code)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)

        web_view.page().scripts().insert(script)

    # ------------------------------------------------------------------
    # Window controls
    # ------------------------------------------------------------------

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _apply_title_bar_style(self):
        """Derive title-bar styles from the system palette."""
        pal = self.palette()
        fg = pal.color(QPalette.ColorRole.WindowText).name()
        border = pal.color(QPalette.ColorRole.Mid).name()
        bg = pal.color(QPalette.ColorRole.Window).name()
        hover = pal.color(QPalette.ColorRole.Midlight).name()

        btn_style = (
            f"QPushButton {{ border: none; font-size: 14px; padding: 0; color: {fg}; }}"
            f" QPushButton:hover {{ background: {hover}; }}"
        )
        self.minimize_button.setStyleSheet(btn_style)
        self.maximize_button.setStyleSheet(btn_style)
        self.close_button.setStyleSheet(btn_style)

        self.title_bar.setStyleSheet(f"""
            _TitleBarWidget {{
                border-bottom: 1px solid {border};
                background-color: {bg};
            }}
        """)

        self.setStyleSheet(f"WebShellWindow {{ border: 1px solid {border}; }}")

    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:
            self._apply_title_bar_style()
        elif event.type() == QEvent.Type.WindowStateChange:
            m = 0 if self.isMaximized() else _RESIZE_GRIP
            self.layout().setContentsMargins(m, m, m, m)
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Frameless resize handling
    # ------------------------------------------------------------------

    @staticmethod
    def _edges_at(pos, size):
        edges = Qt.Edge(0)
        if pos.x() < _RESIZE_GRIP:
            edges |= Qt.Edge.LeftEdge
        if pos.x() >= size.width() - _RESIZE_GRIP:
            edges |= Qt.Edge.RightEdge
        if pos.y() < _RESIZE_GRIP:
            edges |= Qt.Edge.TopEdge
        if pos.y() >= size.height() - _RESIZE_GRIP:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _update_edge_cursor(self):
        if self.isMaximized():
            self.unsetCursor()
            return
        local = self.mapFromGlobal(QCursor.pos())
        edges = self._edges_at(local, self.size())
        e = edges.value
        if not e:
            self.unsetCursor()
            return
        L, R = Qt.Edge.LeftEdge.value, Qt.Edge.RightEdge.value
        T, B = Qt.Edge.TopEdge.value, Qt.Edge.BottomEdge.value
        if e == (L | T) or e == (R | B):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif e == (R | T) or e == (L | B):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif e & (L | R):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeVerCursor)

    def event(self, ev):
        t = ev.type()
        if t in (QEvent.Type.HoverMove, QEvent.Type.MouseMove):
            self._update_edge_cursor()
        elif t == QEvent.Type.Leave:
            self.unsetCursor()
        return super().event(ev)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            edges = self._edges_at(event.position().toPoint(), self.size())
            if edges:
                self.windowHandle().startSystemResize(edges)
                event.accept()
                return
        super().mousePressEvent(event)

    # ------------------------------------------------------------------
    # Resize (dev tools layout)
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.dev_tools_view and self.dev_tools_view.isVisible():
            w = self.width()
            h = self.height()
            ratio = w / h if h > 0 else 1.0
            if ratio > 1.3:
                self.content_area.setOrientation(Qt.Orientation.Horizontal)
            else:
                self.content_area.setOrientation(Qt.Orientation.Vertical)


class _TitleBarWidget(QWidget):
    """Draggable title-bar area that lets the user move the frameless window."""

    def __init__(self, window: "WebShellWindow", parent=None):
        super().__init__(parent or window)
        self._window = window

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._window.windowHandle().startSystemMove()
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._window.isMaximized():
                self._window.showNormal()
            else:
                self._window.showMaximized()
