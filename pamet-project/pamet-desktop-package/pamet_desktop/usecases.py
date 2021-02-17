import pamet
from pamet.entities import Page
import misli_gui
from misli_gui.actions_lib import action
from pamet_desktop.config import get_config


@action('desktop.new_browser_window_ensure_page')
def new_browser_window_ensure_page():
    desktop_config = get_config()
    if 'home_page_id' in desktop_config:
        raise NotImplementedError()  # Load from id/url

    pages = pamet.pages()
    if not pages:
        page = Page(id='notes', obj_class='MapPage')
        pamet.add_page(page, notes=[])
    else:
        page = pages[0]

    new_browser_window(page.id)


@action('desktop.new_browser_window')
def new_browser_window(page_id: str):
    app = misli_gui.find_component(obj_class='DesktopApp')
    window = misli_gui.create_component(
        obj_class='BrowserWindow', parent_id=app.id)

    # new_window =
    # app.window_ids.add(window.id)
    # misli_gui.update_component(app)

    new_browser_tab(window.id, page_id)


@action('desktop.close_browser_window')
def close_browser_window(browser_window_id: str):
    browser_window = misli_gui.component(browser_window_id)
    misli_gui.remove_component(browser_window)
    # app = misli_gui.find_component(obj_class='DesktopApp')
    # app.should_quit = True
    # misli_gui.update_component(app.id)


@action('desktop.new_browser_tab')
def new_browser_tab(browser_window_id: str, page_id: str):
    tab_component = misli_gui.create_component(
        obj_class='BrowserTab', parent_id=browser_window_id)

    tab_go_to_page(tab_component.id, page_id)


@action('tab_go_to_page')
def tab_go_to_page(tab_component_id, page_id):
    page = pamet.page(page_id)
    page_component = pamet.create_and_bind_page_component(
        page.id, parent_id=tab_component_id)

    page_component_state = misli_gui.component_state(page_component.id)
    page_component_state.page = page

    tab_component_state = misli_gui.component_state(tab_component_id)
    tab_component_state.page_component_id = page_component.id

    misli_gui.update_component_state(tab_component_state)
    misli_gui.update_component_state(page_component_state)