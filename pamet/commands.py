from __future__ import annotations
from pathlib import Path
from typing import Tuple
from PySide6.QtCore import QUrl
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

import fusion
from fusion.util.point2d import Point2D
from fusion.libs.command import command
from pamet import desktop_app
import pamet

from pamet.actions import note as note_actions
from pamet.actions import map_page as map_page_actions
from pamet.actions import tab as tab_actions
from pamet.actions import window as window_actions

from pamet.desktop_app.util import resource_path, current_window, current_tab
from pamet.views.note.base.state import NoteViewState

log = fusion.get_logger(__name__)


def current_tab_and_page_views() -> Tuple[TabWidget, MapPageWidget]:
    tab = current_tab()
    if not tab:
        raise Exception('There\'s no open tab.')

    page_view = tab.page_view()
    if not page_view:
        raise Exception('No page view.')

    return tab, page_view


@command(title='Create new note')
def create_new_note():
    current_window().current_tab().create_new_note_command()


@command(title='Create new page')
def create_new_page():
    current_window().current_tab().create_new_page_command()


@command(title='Open page properties')
def open_page_properties():
    tab, page_view = current_tab_and_page_views()
    map_page_actions.open_page_properties(tab.state())


@command(title='Edit selected note')
def edit_selected_notes():
    tab, page_view = current_tab_and_page_views()

    for note_state in page_view.state().selected_children:
        if not isinstance(note_state, NoteViewState):
            continue
        note_actions.start_editing_note(tab.state(), note_state.get_note())


@command(title='Show all commands')
def open_command_palette():
    window_actions.open_command_view(current_window().state(), prefix='>')


@command(title='Go to file')
def open_command_palette_go_to_file():
    window_actions.open_command_view(current_window().state())


@command(title='Create an arrow')
def start_arrow_creation():
    _, page_view = current_tab_and_page_views()

    map_page_actions.start_arrow_creation(page_view.state())


@command(title='Resize selected notes to fit text')
def autosize_selected_notes():
    _, page_view = current_tab_and_page_views()
    map_page_actions.autosize_selected_notes(page_view.state())
    page_view.autosize_selected_notes()


@command(title='Undo')
def undo():
    _, page_view = current_tab_and_page_views()
    map_page_actions.undo(page_view.state())


@command(title='Redo')
def redo():
    _, page_view = current_tab_and_page_views()
    map_page_actions.redo(page_view.state())


@command(title='Copy')
def copy():
    _, page_view = current_tab_and_page_views()

    q_mouse_pos = page_view.mapFromGlobal(QCursor.pos())
    mouse_pos = Point2D(q_mouse_pos.x(), q_mouse_pos.y())
    map_page_state = page_view.state()
    unproj_mouse_pos = map_page_state.unproject_point(mouse_pos)
    map_page_actions.copy_selected_children(map_page_state, unproj_mouse_pos)


@command(title='Paste')
def paste():
    _, page_view = current_tab_and_page_views()
    q_mouse_pos = page_view.mapFromGlobal(QCursor.pos())
    mouse_pos = Point2D(q_mouse_pos.x(), q_mouse_pos.y())
    map_page_state = page_view.state()
    unproj_mouse_pos = map_page_state.unproject_point(mouse_pos)
    map_page_actions.paste(map_page_state, unproj_mouse_pos)


@command(title='Cut')
def cut():
    _, page_view = current_tab_and_page_views()
    q_mouse_pos = page_view.mapFromGlobal(QCursor.pos())
    mouse_pos = Point2D(q_mouse_pos.x(), q_mouse_pos.y())
    map_page_state = page_view.state()
    unproj_mouse_pos = map_page_state.unproject_point(mouse_pos)
    map_page_actions.cut_selected_children(map_page_state, unproj_mouse_pos)


@command(title='Paste special')
def paste_special():
    _, page_view = current_tab_and_page_views()
    q_mouse_pos = page_view.mapFromGlobal(QCursor.pos())
    mouse_pos = Point2D(q_mouse_pos.x(), q_mouse_pos.y())
    map_page_state = page_view.state()
    unproj_mouse_pos = map_page_state.unproject_point(mouse_pos)
    map_page_actions.paste_special(map_page_state, unproj_mouse_pos)


@command(title='Show search')
def show_global_search():
    tab_view, _ = current_tab_and_page_views()
    tab_actions.open_global_search(tab_view.state())


@command(title='Close tab')
def close_current_tab():
    window = current_window()
    tab = window.current_tab()
    window_actions.close_tab(window.state(), tab.state())


@command(title='Open user settings (JSON)')
def open_user_settings_json():
    settings_path = desktop_app.user_settings_path()
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(settings_path)))


@command(title='Open repo settings (JSON)')
def open_repo_settings_json():
    settings_path = desktop_app.repo_settings_path(pamet.sync_repo().path)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(settings_path)))


@command(title='Export as web page')
def export_as_web_page():
    tab_view, page_view = current_tab_and_page_views()

    note_elements = []
    for nt_view in page_view.note_views():
        nv_state = nt_view.state()
        r = nv_state.rect()

        color_vals = [c * 100 for c in nv_state.color]
        color_str = ', '.join([f'{c}%' for c in color_vals])
        color_str = f'rgba({color_str})'

        bg_color_vals = [c * 100 for c in nv_state.background_color]
        bg_color_str = ', '.join([f'{c}%' for c in bg_color_vals])
        bg_color_str = f'rgba({bg_color_str})'

        note_style = (f'top: {r.y()}; left: {r.x()};'
                      f'width: {r.width()};height: {r.height()};')
        note_style += f' color: {color_str};'
        note_style += f' background: {bg_color_str};'

        note_el_props = {
            'id': nv_state.id,
            'class': 'note',
        }
        if nv_state.url.is_external():
            note_el_props['href'] = nv_state.url
            note_style += f'border: 1px solid {color_str};'

        note_el_props['style'] = note_style

        props_str = ' '.join([f'{k}="{v}"' for k, v in note_el_props.items()])
        # id="{nv_state.id}" class="note" style="{note_style}"
        note_el = f'''
        <a {props_str}>
            {nt_view.displayed_text}
        </a>
        '''
        note_elements.append(note_el)

    note_elements_str = "\n".join(note_elements)
    page_script = resource_path('static_page_src/script.js').read_text()
    page_style = resource_path('static_page_src/style.css').read_text()
    page_str = f'''
    <html>
        <head>
            <style>
            {page_style}
            </style>
        </head>
        <body>
            <div id="mapPage">
{note_elements_str}
            </div>

            <script>
                {page_script}
            </script>
        </body>
    </html>
    '''

    # A dummy widget, because QFileDialog crashed the app without it
    widget = QWidget()
    path, _ = QFileDialog.getSaveFileName(widget, 'Choose save path')
    widget.deleteLater()

    if not path:
        return
    path = Path(path)
    path.write_text(page_str)
