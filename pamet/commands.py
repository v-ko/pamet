from __future__ import annotations
from pathlib import Path
from typing import Tuple

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog

import fusion
from fusion.util.point2d import Point2D
from fusion.libs.command import command
from pamet import desktop_app, semantic_search_service
import pamet

from pamet.actions import note as note_actions
from pamet.actions import map_page as map_page_actions
from pamet.actions import tab as tab_actions
from pamet.actions import window as window_actions
from pamet.constants import GREEN_FG_COLOR

from pamet.desktop_app.util import current_window, current_tab
from pamet.model.text_note import TextNote
from pamet.util import resource_path
from pamet.views.note.base.state import NoteViewState
from pamet.views.note.image.widget import ImageNoteWidget

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
    tab_widget, page_widget = current_tab_and_page_views()

    # If the mouse is on the page - make the note on its position.
    # Else: make it in the center of the viewport
    if page_widget.underMouse():
        edit_window_pos = page_widget.mapFromGlobal(QCursor.pos())
    else:
        edit_window_pos = page_widget.geometry().center()

    edit_window_pos = Point2D(edit_window_pos.x(), edit_window_pos.y())

    note_pos = page_widget.state().unproject_point(edit_window_pos)
    new_note = TextNote()
    new_note = new_note.with_id(page_id=page_widget.state().page_id)
    new_note.x = note_pos.x()
    new_note.y = note_pos.y()
    note_actions.create_new_note(tab_widget.state(), new_note)


@command(title='Create new page')
def create_new_page():
    tab_widget = current_window().current_tab()
    page_widget = tab_widget.page_view()
    mouse_pos = page_widget.mapFromGlobal(QCursor.pos())
    edit_window_pos = Point2D(mouse_pos.x(), mouse_pos.y())
    tab_actions.create_new_page(tab_widget.state(), edit_window_pos)


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


@command(title='Delete selected')
def delete_selected():
    _, page_view = current_tab_and_page_views()
    map_page_actions.delete_selected_children(page_view.state())


@command(title='Show search')
def show_global_search():
    tab_view, _ = current_tab_and_page_views()
    tab_actions.open_global_search(tab_view.state())


@command(title='Show semantic search (experimental')
def show_semantic_search():
    tab_view, _ = current_tab_and_page_views()
    if not semantic_search_service():
        raise Exception('Semantic search is not available.'
                        'Itt\'s either broken or you have not enabled it '
                        'in the repo settings.')
    tab_actions.open_semantic_search(tab_view.state())


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
        # Skip images
        if isinstance(nt_view, ImageNoteWidget):
            continue

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

    # Hackily present the file chooser modal
    # (otherwise the app crashes when the modal is closed)
    file_name = f'{tab_view.state().title}.html'

    def hackily_ask_for_path_and_save_file():
        file_dialog = QFileDialog(parent=page_view)
        path, _ = file_dialog.getSaveFileName(
            None,
            caption='Choose save path',
            dir=file_name,
            filter='*.html',
        )

        if not path:
            return
        path = Path(path)
        path.write_text(page_str)

    QTimer.singleShot(0, hackily_ask_for_path_and_save_file)


@command(title='Grab screen snippet')
def grab_screen_snippet():
    active_window = current_window()
    if not active_window:
        # Minimize all non-active windows
        # (so that the screenshot doesn't include them. It's a problem on KDE)
        for window in QApplication.instance().topLevelWidgets():
            if window != QApplication.activeWindow():
                window.setWindowState(Qt.WindowMinimized)

    desktop_app.get_app().selector_widget.showFullScreen()


@command(title='Refresh page')
def refresh_page():
    tab_view, page_view = current_tab_and_page_views()

    # Remove view cache
    if page_view:
        tab_view.clear_page_view()
        tab_view.remove_page_widget_from_cache(page_view.state().view_id)
    tab_actions.refresh_page(tab_view.state())


@command(title='Color selected notes blue')
def color_selected_notes_blue():
    _, page_view = current_tab_and_page_views()
    map_page_actions.color_selected_children(page_view.state(),
                                             color=[0, 0, 1, 1],
                                             background_color=[0, 0, 1, 0.1])


@command(title='Color selected notes green')
def color_selected_notes_green():
    _, page_view = current_tab_and_page_views()
    map_page_actions.color_selected_children(page_view.state(),
                                             color=list(GREEN_FG_COLOR),
                                             background_color=[0, 1, 0, 0.1])


@command(title='Color selected notes red')
def color_selected_notes_red():
    _, page_view = current_tab_and_page_views()
    map_page_actions.color_selected_children(page_view.state(),
                                             color=[1, 0, 0, 1],
                                             background_color=[1, 0, 0, 0.1])


@command(title='Color selected notes black')
def color_selected_notes_black():
    _, page_view = current_tab_and_page_views()
    map_page_actions.color_selected_children(page_view.state(),
                                             color=[0, 0, 0, 1],
                                             background_color=[0, 0, 0, 0.1])


@command(title='Make background transparent for selected notes')
def make_background_transparent_for_selected_notes():
    _, page_view = current_tab_and_page_views()
    map_page_actions.color_selected_children(page_view.state(),
                                             background_color=[0, 0, 0, 0])


@command(title='Blue shift selected')
def blue_shift_selected():
    _, page_view = current_tab_and_page_views()
    map_page_actions.shift_selected_childrens_color(page_view.state(),
                                                    fg_mask=(False, False,
                                                             True, False),
                                                    bg_mask=(False, False,
                                                             True, False))


@command(title='Green shift selected')
def green_shift_selected():
    _, page_view = current_tab_and_page_views()
    map_page_actions.shift_selected_childrens_color(page_view.state(),
                                                    fg_mask=(False, True,
                                                             False, False),
                                                    bg_mask=(False, True,
                                                             False, False))


@command(title='Red shift selected')
def red_shift_selected():
    _, page_view = current_tab_and_page_views()
    map_page_actions.shift_selected_childrens_color(page_view.state(),
                                                    fg_mask=(True, False,
                                                             False, False),
                                                    bg_mask=(True, False,
                                                             False, False))


@command(title='Black shift selected notes')
def black_shift_selected():
    _, page_view = current_tab_and_page_views()
    map_page_actions.shift_selected_childrens_color(page_view.state(),
                                                    fg_mask=(True, True, True,
                                                             False),
                                                    bg_mask=(True, True, True,
                                                             False))


@command(title='Shift selected note transparency')
def shift_selected_note_transparency():
    _, page_view = current_tab_and_page_views()
    map_page_actions.shift_selected_childrens_color(page_view.state(),
                                                    fg_mask=(False, False,
                                                             False, False),
                                                    bg_mask=(False, False,
                                                             False, True),
                                                    shift=-0.0333)


@command(title='Select all')
def select_all():
    _, page_view = current_tab_and_page_views()
    map_page_actions.select_all_children(page_view.state())


@command(title='Navigate back')
def navigate_back():
    tab_view, _ = current_tab_and_page_views()
    tab_actions.navigation_back(tab_view.state())


@command(title='Navigate forward')
def navigate_forward():
    tab_view, _ = current_tab_and_page_views()
    tab_actions.navigation_forward(tab_view.state())


@command(title='Toggle between last two pages')
def toggle_between_last_two_pages():
    tab_view, _ = current_tab_and_page_views()
    tab_actions.navigation_toggle_last(tab_view.state())
