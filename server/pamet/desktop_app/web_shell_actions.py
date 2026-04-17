from pamet.desktop_app.web_shell_view_state import WebShellViewState


def close_tab(state: WebShellViewState, index: int) -> None:
    """Close the tab at *index*. If it's the last tab the caller should
    close the window (signalled via the state having zero tabs)."""
    if index < 0 or index >= len(state.tabs):
        return
    state.remove_tab(index)
