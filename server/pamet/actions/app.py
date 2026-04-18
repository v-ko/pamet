from fusion.libs.action import action

from pamet.views.app_window.app_window_view_state import AppWindowViewState


@action("window.close_tab")
def close_tab(state: AppWindowViewState, index: int) -> None:
    """Close the tab at *index*. If it's the last tab the caller should
    close the window (signalled via the state having zero tabs)."""
    if index < 0 or index >= len(state.tabs):
        return
    state.remove_tab(index)
