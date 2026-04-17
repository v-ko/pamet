from __future__ import annotations

from dataclasses import dataclass
from typing import List

from fusion.platform.qt_widgets import Property
from PySide6.QtCore import QObject, Signal


@dataclass
class TabState:
    """Lightweight descriptor for a single browser tab."""

    tab_id: str
    title: str = "Untitled"
    url: str = ""


class WebShellViewState(QObject):
    """Qt-backed view state for the WebShell window (flux-style)."""

    title_changed = Signal(str)
    tabs_changed = Signal()
    current_tab_index_changed = Signal(int)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._title = "Pamet"
        self._tabs: List[TabState] = []
        self._current_tab_index = -1

    # --- title ---
    @Property(str, notify=title_changed)
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        if self._title == value:
            return
        self._title = value
        self.title_changed.emit(value)

    # --- tabs ---
    @property
    def tabs(self) -> List[TabState]:
        return self._tabs

    # --- current_tab_index ---
    @Property(int, notify=current_tab_index_changed)
    def current_tab_index(self) -> int:
        return self._current_tab_index

    @current_tab_index.setter
    def current_tab_index(self, value: int) -> None:
        if self._current_tab_index == value:
            return
        self._current_tab_index = value
        self.current_tab_index_changed.emit(value)

    # --- helpers ---

    @property
    def current_tab(self) -> TabState | None:
        if 0 <= self._current_tab_index < len(self._tabs):
            return self._tabs[self._current_tab_index]
        return None

    def add_tab(self, tab: TabState, switch_to: bool = True) -> None:
        self._tabs.append(tab)
        self.tabs_changed.emit()
        if switch_to:
            self.current_tab_index = len(self._tabs) - 1

    def remove_tab(self, index: int) -> None:
        if index < 0 or index >= len(self._tabs):
            return
        self._tabs.pop(index)
        self.tabs_changed.emit()
        # Adjust current index
        if len(self._tabs) == 0:
            self.current_tab_index = -1
        elif self._current_tab_index >= len(self._tabs):
            self.current_tab_index = len(self._tabs) - 1
        elif self._current_tab_index == index:
            # Re-emit to force refresh even if numeric value unchanged
            self.current_tab_index_changed.emit(self._current_tab_index)

    def update_tab_title(self, index: int, title: str) -> None:
        if 0 <= index < len(self._tabs):
            self._tabs[index].title = title
            self.tabs_changed.emit()

    def update_tab_url(self, index: int, url: str) -> None:
        if 0 <= index < len(self._tabs):
            self._tabs[index].url = url
