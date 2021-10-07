import misli
from misli import gui
from misli.gui.actions_library import action

import pamet
from pamet.model import Page
from pamet.desktop.config import get_config
from pamet.views.desktop.window_view_widget import BrowserWindowView
from pamet.views.desktop.tab_view_widget import BrowserTabViewWidget


@action('desktop.new_browser_window_ensure_page')
def new_browser_window_ensure_page():
    desktop_config = get_config()
    if 'home_page_id' in desktop_config:
        raise NotImplementedError()  # Load from id/url

    pages = list(pamet.pages())
    if not pages:
        page = Page(name='notes')
        misli.insert(page)
    else:
        page = pages[0]

    new_browser_window(page.id)


@action('desktop.new_browser_window')
def new_browser_window(page_id: str):
    window: BrowserWindowView = gui.create_view(
        parent_id=None, view_class_name=BrowserWindowView.__name__)

    new_browser_tab(window.id, page_id)


@action('desktop.close_browser_window')
def close_browser_window(browser_window_id: str):
    browser_window = gui.view(browser_window_id)
    gui.remove_view(browser_window)


@action('desktop.new_browser_tab')
def new_browser_tab(browser_window_id: str, page_id: str):
    tab_view: BrowserTabViewWidget = gui.create_view(
        parent_id=browser_window_id, view_class_name=BrowserTabViewWidget.__name__)

    tab_go_to_page(tab_view.id, page_id)


@action('tab_go_to_page')
def tab_go_to_page(tab_component_id, page_id):
    page = pamet.page(gid=page_id)
    page_view = pamet.create_and_bind_page_view(
        page.id, parent_id=tab_component_id)

    page_view_state = gui.view_state(page_view.id)
    page_view_state.page = page

    tab_view_state = gui.view_state(tab_component_id)
    tab_view_state.page_view_id = page_view.id
    tab_view_state.name = page.name

    gui.update_state(tab_view_state)
    gui.update_state(page_view_state)


@action('tab_go_to_default_page')
def tab_go_to_default_page(tab_component_id):
    pass
