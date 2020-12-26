import misli
from misli.gui.actions_lib import action
from misli.gui.desktop.config import get_config


@action('desktop.new_browser_window')
def new_browser_window(page_id: str):
    app = misli.gui.find_component(obj_class='DesktopApp')

    window = misli.gui.create_component(
        obj_class='BrowserWindow', parent_id=app.id)

    new_browser_tab(window.id, page_id)


@action('desktop.new_browser_tab')
def new_browser_tab(browser_window_id: str, page_id: str):
    tab = misli.gui.create_component(
        obj_class='BrowserTab', parent_id=browser_window_id)

    tab.current_page_id = page_id
    misli.gui.update_component(tab.id)


@action('desktop.new_browser_window_ensure_page')
def new_browser_window_ensure_page():
    desktop_config = get_config()
    if 'home_page_id' in desktop_config:
        raise NotImplementedError()  # Load from id/url

    pages = misli.pages()
    if not pages:
        page = misli.create_page(id='notes', obj_class='MapPage')
    else:
        page = pages[0]

    new_browser_window(page.id)


@action('desktop.close_browser_window')
def close_browser_window(browser_window_id: str):
    misli.gui.remove_component(browser_window_id)
    # app = misli.gui.find_component(obj_class='DesktopApp')
    # app.should_quit = True
    # misli.gui.update_component(app.id)
