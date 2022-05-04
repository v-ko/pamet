from __future__ import annotations
import misli.gui
from misli.gui.actions_library import action
from pamet.views.tab.widget import TabViewState
from pamet.views.window import widget as window_widget

from pamet.actions import tab as tab_actions
from pamet.views.window.widget import WindowViewState


@action('desktop_app.new_browser_window')
def new_browser_window():
    window_state = WindowViewState()
    misli.gui.add_state(window_state)
    return window_state


@action('desktop_app.new_browser_tab')
def new_browser_tab(window_state: window_widget.WindowViewState, page: str):
    tab_state = TabViewState()
    misli.gui.add_state(tab_state)

    window_state.tab_states.append(tab_state)
    misli.gui.update_state(window_state)

    tab_actions.tab_go_to_page(tab_state, page)
