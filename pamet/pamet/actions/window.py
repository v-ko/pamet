from misli import gui
from misli.gui.actions_library import action

from pamet.views.window.widget import BrowserWindowWidget
from pamet.views.tab.widget import TabWidget
from pamet.actions import tab as tab_actions
from pamet import commands


@action('desktop_app.new_browser_window')
def new_browser_window(page_id: str):
    window: BrowserWindowWidget = gui.create_view(
        parent_id=None, view_class_name=BrowserWindowWidget.__name__)

    new_browser_tab(window.id, page_id)


@action('desktop_app.close_browser_window')
def close_browser_window(browser_window_id: str):
    browser_window = gui.view(browser_window_id)
    gui.remove_view(browser_window)


@action('desktop_app.new_browser_tab')
def new_browser_tab(browser_window_id: str, page_id: str):
    tab_view: TabWidget = gui.create_view(
        parent_id=browser_window_id,
        view_class_name=TabWidget.__name__)

    tab_actions.tab_go_to_page(tab_view.id, page_id)


@action('window.open_main_menu')
def open_main_menu(window_view_id):
    entries = {
        'Page properties': commands.open_page_properties
    }
    gui.create_view(
        window_view_id,
        view_class_metadata_filter=dict(name='ContextMenu'),
        init_kwargs=dict(entries=entries))
