from misli import gui
from misli.gui.actions_lib import action

import pamet
from pamet.map_page.entity import MapPage
from pamet.desktop.config import get_config


@action('desktop.new_browser_window_ensure_page')
def new_browser_window_ensure_page():
    desktop_config = get_config()
    if 'home_page_id' in desktop_config:
        raise NotImplementedError()  # Load from id/url

    pages = pamet.pages()
    if not pages:
        page = MapPage(name='notes')
        pamet.add_page(page, _notes=[])
    else:
        page = pages[0]

    new_browser_window(page.id)


@action('desktop.new_browser_window')
def new_browser_window(page_id: str):
    app = gui.find_view(class_name='DesktopApp')

    window_view_class = gui.view_library.get_view_class('BrowserWindowView')
    window = window_view_class(parent_id=app.id)

    new_browser_tab(window.id, page_id)


@action('desktop.close_browser_window')
def close_browser_window(browser_window_id: str):
    browser_window = gui.view(browser_window_id)
    gui.remove_view(browser_window)


@action('desktop.new_browser_tab')
def new_browser_tab(browser_window_id: str, page_id: str):
    # tab_view = gui.create_view(
    #     obj_class='BrowserTab', parent_id=browser_window_id)

    tab_view_class = gui.view_library.get_view_class('BrowserTabView')
    tab_view = tab_view_class(parent_id=browser_window_id)

    tab_go_to_page(tab_view.id, page_id)


@action('tab_go_to_page')
def tab_go_to_page(tab_component_id, page_id):
    page = pamet.page(page_id)
    page_view = pamet.create_and_bind_page_view(
        page.id, parent_id=tab_component_id)

    page_view_model = gui.view_model(page_view.id)
    page_view_model.page = page

    tab_view_model = gui.view_model(tab_component_id)
    tab_view_model.page_view_id = page_view.id

    gui.update_view_model(tab_view_model)
    gui.update_view_model(page_view_model)