import misli
from pamet.views.tab.view import BrowserTabView
from pamet.views.window.view import BrowserWindowView


def current_window() -> BrowserWindowView:
    return misli.gui.focused_view_or_parent(view_type=BrowserWindowView)


def current_tab():
    return current_window().current_tab()
