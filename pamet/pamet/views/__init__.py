import misli
from pamet.views.tab.view import BrowserTabView


def current_tab():
    return misli.gui.focused_view_or_parent(view_type=BrowserTabView)
