from misli import misli
from misli.gui.desktop.config import get_config


def new_browser_window(page_id):
    app = misli.desktop_app()

    window = misli.create_component(
        obj_class='BrowserWindow', parent_id=app.id)

    new_browser_tab(window.id, page_id)


def new_browser_tab(browser_window_id, page_id):
    tab = misli.create_component(
        obj_class='BrowserTab', parent_id=browser_window_id)

    tab.current_page_id = page_id
    misli.update_component(tab.id)


def new_browser_window_ensure_page():
    desktop_config = get_config()
    if 'home_page_id' in desktop_config:
        raise NotImplementedError()  # Load from id/url
        return

    pages = misli.pages()
    if not pages:
        page = misli.create_page(id='notes', obj_class='MapPage')
    else:
        page = pages[0]

    new_browser_window(page.id)