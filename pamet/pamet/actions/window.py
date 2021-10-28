from misli import gui
from misli.gui.actions_library import action

from pamet.views.window.window_view_widget import BrowserWindowViewWidget
from pamet.views.tab.widget import BrowserTabViewWidget
from pamet.actions import tab as tab_actions


@action('desktop_app.new_browser_window')
def new_browser_window(page_id: str):
    window: BrowserWindowViewWidget = gui.create_view(
        parent_id=None, view_class_name=BrowserWindowViewWidget.__name__)

    new_browser_tab(window.id, page_id)


@action('desktop_app.close_browser_window')
def close_browser_window(browser_window_id: str):
    browser_window = gui.view(browser_window_id)
    gui.remove_view(browser_window)


@action('desktop_app.new_browser_tab')
def new_browser_tab(browser_window_id: str, page_id: str):
    tab_view: BrowserTabViewWidget = gui.create_view(
        parent_id=browser_window_id,
        view_class_name=BrowserTabViewWidget.__name__)

    tab_actions.tab_go_to_page(tab_view.id, page_id)
