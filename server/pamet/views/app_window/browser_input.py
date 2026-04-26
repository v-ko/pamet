"""Keyboard routing between the Qt shell and the embedded QWebEngineView.

QWebEngineView has a hidden child widget (the "focus proxy") that talks
to the Chromium renderer.  We install event filters on both the web view
and its proxy so we can intercept Tab for boundary navigation.

When a Qt shell widget (button, tab bar) has focus, unhandled keys
propagate up to AppWindow.keyPressEvent → handle_key_event, which
forwards them to Chromium so JS keybindings still work.  When focus is
already on the web view side, Chromium gets the key natively — we must
NOT forward it again or the async bounce-back creates an infinite loop.
"""

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QPushButton, QWidget


class BrowserInput(QObject):

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._sending_tab = False
        self._proxies: dict[int, QWidget] = {}  # id(web_view) → proxy

    def _current_web_view(self) -> QWebEngineView | None:
        stack = self.parent().stack  # type: ignore[union-attr]
        w = stack.currentWidget()
        return w if isinstance(w, QWebEngineView) else None

    # -- Setup ---------------------------------------------------------

    def install_on_web_view(self, web_view: QWebEngineView) -> None:
        web_view.installEventFilter(self)
        self._poll_for_proxy(web_view, attempts_left=20)

    def _poll_for_proxy(self, wv: QWebEngineView, attempts_left: int) -> None:
        proxy = wv.focusProxy()
        if proxy:
            proxy.installEventFilter(self)
            self._proxies[id(wv)] = proxy
            return
        if attempts_left > 0:
            QTimer.singleShot(50, lambda: self._poll_for_proxy(wv, attempts_left - 1))

    # -- Shell key handling (AppWindow.keyPressEvent) ------------------

    def handle_key_event(self, event: QKeyEvent) -> None:
        if event.isAccepted():
            return

        key = event.key()
        fw = QApplication.focusWidget()

        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            return  # Handled by event filter

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if isinstance(fw, QPushButton):
                fw.animateClick()
                event.accept()
                return

        self._forward_to_chromium(event, fw)

    def _forward_to_chromium(self, event: QKeyEvent, fw: QWidget | None) -> None:
        wv = self._current_web_view()
        if not wv:
            return
        proxy = self._proxies.get(id(wv))
        if not proxy:
            return
        # If focus is already on the web view side, Chromium got the key
        # natively.  Forwarding it again causes an infinite loop.
        if fw is proxy or fw is wv:
            return
        self._send_key(proxy, event.key(), event.modifiers(), event.text())
        event.accept()

    # -- Event filter (Tab boundary) -----------------------------------

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if not isinstance(event, QKeyEvent):
            return False
        if event.type() != QEvent.Type.KeyPress:
            return False
        if event.key() not in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            return False
        if self._sending_tab:
            return False  # Let our synthetic Tab through

        wv = self._web_view_for(obj)
        if wv is None:
            return False

        self._handle_tab_boundary(wv, event)
        return True

    # -- Tab boundary navigation ---------------------------------------

    def _handle_tab_boundary(self, web_view: QWebEngineView, event: QKeyEvent) -> None:
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        js_expr = (
            "pamet.focusManager.atFirstTabIndex()"
            if shift
            else "pamet.focusManager.atLastTabIndex()"
        )
        window = web_view.window()

        def _on_result(at_boundary: bool) -> None:
            if at_boundary:
                if shift:
                    window.focusPreviousChild()
                else:
                    window.focusNextChild()
            else:
                key = Qt.Key.Key_Backtab if shift else Qt.Key.Key_Tab
                mods = (
                    Qt.KeyboardModifier.ShiftModifier
                    if shift
                    else Qt.KeyboardModifier.NoModifier
                )
                self._send_tab(web_view, key, mods)

        web_view.page().runJavaScript(js_expr, _on_result)

    def _send_tab(
        self, web_view: QWebEngineView, key: Qt.Key, modifiers: Qt.KeyboardModifier
    ) -> None:
        proxy = self._proxies.get(id(web_view))
        if not proxy:
            return
        self._sending_tab = True
        try:
            self._send_key(proxy, key, modifiers)
        finally:
            self._sending_tab = False

    # -- Helpers -------------------------------------------------------

    def send_key_to_chromium(
        self,
        web_view: QWebEngineView,
        key: Qt.Key,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
        text: str = "",
    ) -> bool:
        proxy = self._proxies.get(id(web_view))
        if not proxy:
            return False
        self._send_key(proxy, key, modifiers, text)
        return True

    def _send_key(
        self,
        target: QWidget,
        key: int,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
        text: str = "",
    ) -> None:
        target.event(QKeyEvent(QEvent.Type.KeyPress, key, modifiers, text))
        target.event(QKeyEvent(QEvent.Type.KeyRelease, key, modifiers, text))

    def _web_view_for(self, obj: QObject) -> QWebEngineView | None:
        if isinstance(obj, QWebEngineView) and id(obj) in self._proxies:
            return obj
        parent = obj.parent()
        if isinstance(parent, QWebEngineView) and id(parent) in self._proxies:
            return parent
        return None
