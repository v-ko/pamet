from __future__ import annotations

from fusion import fsm
from fusion.libs.action import action
from fusion.libs.state import ViewState
from pamet.model.page import Page
from pamet.views.command_palette.widget import CommandPaletteViewState
from pamet.views.tab.state import TabViewState

from pamet.actions import tab as tab_actions
from pamet.views.window.state import WindowViewState


@action('window.new_browser_window')
def new_browser_window():
    window_state = WindowViewState()
    fsm.add_state(window_state)
    return window_state


@action('window.new_browser_tab')
def new_browser_tab(window_state: WindowViewState, page: Page):
    tab_state = TabViewState()
    fsm.add_state(tab_state)

    window_state.tab_states.append(tab_state)
    fsm.update_state(window_state)

    tab_actions.go_to_url(tab_state, page.url())


@action('window.close_tab')
def close_tab(window_state: WindowViewState, tab_state: TabViewState):
    window_state.tab_states.remove(tab_state)
    fsm.update_state(window_state)


@action('window.open_command_view')
def open_command_view(window_state: WindowViewState,
                      prefix: str = '',
                      command_view_state: ViewState = None):

    if not command_view_state:
        command_view_state = CommandPaletteViewState(line_edit_text=prefix)
        fsm.add_state(command_view_state)

    window_state.command_view_state = command_view_state
    fsm.update_state(window_state)


@action('window.close_command_view')
def close_command_view(window_state: WindowViewState):
    window_state.command_view_state = None
    fsm.update_state(window_state)
