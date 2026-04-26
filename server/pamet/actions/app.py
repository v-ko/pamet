"""Actions for the app window shell.

All state mutations go through @action-decorated functions.
The QML backend calls these — it never mutates state directly.
"""

from uuid import uuid4

from fusion.libs.action import action

from pamet.views.app_window.view_state import AppWindowViewState, _Tab

# # Old qt_widgets close_tab (uses widgets-era .tabs / .remove_tab API)
# @action("window.close_tab")
# def close_tab_widgets(state: AppWindowViewState, index: int) -> None:
#     if index < 0 or index >= len(state.tabs):
#         return
#     state.remove_tab(index)


@action("app_window.open_tab")
def open_tab(state: AppWindowViewState, url: str, switch_to: bool = True) -> None:
    tab = _Tab(tab_id=uuid4().hex[:8], url=url)
    row = state._tab_model.append(tab)
    if switch_to:
        state.currentTabIndex = row


@action("app_window.close_tab")
def close_tab(state: AppWindowViewState, index: int) -> None:
    if state._tab_model.count() <= 1:
        state.close_last_tab.emit()
        return
    # Save the URL for Ctrl+Shift+T restore
    tab = state._tab_model._tabs[index]
    if tab.url:
        state._closed_tab_urls.append(tab.url)
    state._tab_model.remove(index)
    n = state._tab_model.count()
    if state._current_tab_index >= n:
        state.currentTabIndex = n - 1
    elif state._current_tab_index == index:
        # Re-emit so QML refreshes even though the numeric index didn't change
        state.current_tab_index_changed.emit(state._current_tab_index)


@action("app_window.close_current_tab")
def close_current_tab(state: AppWindowViewState) -> None:
    if state._current_tab_index >= 0:
        close_tab(state, state._current_tab_index)


@action("app_window.update_tab_title")
def update_tab_title(state: AppWindowViewState, index: int, title: str) -> None:
    state._tab_model.set_title(index, title)


@action("app_window.update_tab_url")
def update_tab_url(state: AppWindowViewState, index: int, url: str) -> None:
    state._tab_model.set_url(index, url)


@action("app_window.update_nav_state")
def update_nav_state(
    state: AppWindowViewState, can_back: bool, can_forward: bool
) -> None:
    state.canGoBack = can_back
    state.canGoForward = can_forward


@action("app_window.next_tab")
def next_tab(state: AppWindowViewState) -> None:
    n = state._tab_model.count()
    if n > 1:
        state.currentTabIndex = (state._current_tab_index + 1) % n


@action("app_window.previous_tab")
def previous_tab(state: AppWindowViewState) -> None:
    n = state._tab_model.count()
    if n > 1:
        state.currentTabIndex = (state._current_tab_index - 1) % n


@action("app_window.switch_to_tab")
def switch_to_tab(state: AppWindowViewState, index: int) -> None:
    if 0 <= index < state._tab_model.count():
        state.currentTabIndex = index


@action("app_window.restore_tab")
def restore_tab(state: AppWindowViewState) -> None:
    if not state._closed_tab_urls:
        return
    url = state._closed_tab_urls.pop()
    open_tab(state, url, switch_to=True)
