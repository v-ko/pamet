from __future__ import annotations

from dataclasses import dataclass

from fusion.platform.qt_widgets import Property
from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt, Signal


# Backward-compat alias for the widgets code path (app_window.py)
@dataclass
class TabState:
    tab_id: str
    title: str = "Untitled"
    url: str = ""


# ── Tab helpers ──────────────────────────────────────────────────────


class _Tab:
    __slots__ = ("tab_id", "title", "url")

    def __init__(self, tab_id: str, url: str, title: str = "Untitled"):
        self.tab_id = tab_id
        self.url = url
        self.title = title


class TabModel(QAbstractListModel):
    """List model for QML Repeater — one WebEngineView per tab."""

    TitleRole = Qt.ItemDataRole.UserRole + 1
    UrlRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._tabs: list[_Tab] = []

    def roleNames(self):
        return {
            self.TitleRole: b"title",
            self.UrlRole: b"url",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._tabs)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        tab = self._tabs[index.row()]
        if role == self.TitleRole:
            return tab.title
        if role == self.UrlRole:
            return tab.url
        return None

    # -- mutations (called from @action functions) --

    def append(self, tab: _Tab) -> int:
        row = len(self._tabs)
        self.beginInsertRows(QModelIndex(), row, row)
        self._tabs.append(tab)
        self.endInsertRows()
        return row

    def remove(self, row: int) -> None:
        if row < 0 or row >= len(self._tabs):
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        self._tabs.pop(row)
        self.endRemoveRows()

    def set_title(self, row: int, title: str) -> None:
        if row < 0 or row >= len(self._tabs):
            return
        self._tabs[row].title = title
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [self.TitleRole])

    def count(self) -> int:
        return len(self._tabs)


# ── View state ───────────────────────────────────────────────────────


class AppWindowViewState(QObject):
    """Pure state for the app window.  Mutated only inside @action functions."""

    current_tab_index_changed = Signal(int)
    close_last_tab = Signal()  # QML connects this to Window.close()
    can_go_back_changed = Signal()
    can_go_forward_changed = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._tab_model = TabModel(self)
        self._current_tab_index = -1
        self._can_go_back = False
        self._can_go_forward = False

    # -- tab model (constant, the object itself never changes) --

    @Property(QObject, constant=True)
    def tabModel(self) -> TabModel:
        return self._tab_model

    # -- current tab index --

    @Property(int, notify=current_tab_index_changed)
    def currentTabIndex(self) -> int:
        return self._current_tab_index

    @currentTabIndex.setter  # type: ignore[attr-defined]
    def currentTabIndex(self, value: int) -> None:
        if self._current_tab_index == value:
            return
        self._current_tab_index = value
        self.current_tab_index_changed.emit(value)

    # -- navigation state --

    @Property(bool, notify=can_go_back_changed)
    def canGoBack(self) -> bool:
        return self._can_go_back

    @canGoBack.setter  # type: ignore[attr-defined]
    def canGoBack(self, value: bool) -> None:
        if self._can_go_back == value:
            return
        self._can_go_back = value
        self.can_go_back_changed.emit()

    @Property(bool, notify=can_go_forward_changed)
    def canGoForward(self) -> bool:
        return self._can_go_forward

    @canGoForward.setter  # type: ignore[attr-defined]
    def canGoForward(self, value: bool) -> None:
        if self._can_go_forward == value:
            return
        self._can_go_forward = value
        self.can_go_forward_changed.emit()
