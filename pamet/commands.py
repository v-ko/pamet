from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import shutil
from typing import Tuple
import uuid

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

import fusion
from fusion.libs.entity import dump_to_dict
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
from pamet.util.url import Url
from pamet.views.arrow.widget import ArrowViewState
from pamet.views.map_page.widget import MapPageWidget
from pamet.views.note.base.state import NoteViewState
from pamet.views.note.image.widget import ImageNoteWidget
from pamet.views.tab.widget import TabWidget

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


@command(title='Export as web page (new) (experimental)')
def export_as_web_page_new():
    # Get the serialized page
    tab_view, page_view = current_tab_and_page_views()
    page_state = page_view.state()

    page = pamet.page(page_state.id)
    page_state = dump_to_dict(page)
    # page_state['notes'] = [dump_to_dict(n) for n in page.notes()]
    # page_state['arrows'] = [dump_to_dict(a) for a in page.arrows()]

    # Ouput folder
    user_settings = desktop_app.get_user_settings()
    export_folder = Path(user_settings.static_export_folder)
    page_exp_folder = export_folder / 'p' / page_state['id']

    # clear the folder
    if page_exp_folder.exists():
        shutil.rmtree(page_exp_folder)
    page_exp_folder.mkdir(parents=True)

    # For each note create a dict with e.g. 'cache' key added with
    note_dicts_by_id = {}
    for note_view in page_view.note_views():
        cache = {
            'text_layout_data': {
                'lines': [],
                'alignment': 'center',
                'is_elided': False,
            },
        }
        note_view_state = note_view.state()

        note = note_view_state.get_note()
        note_dict = dump_to_dict(note)

        if not note_dict['content']:
            continue

        # - Text layout
        if hasattr(note_view, '_elided_text_layout'):
            cache['text_layout_data'] = deepcopy(
                vars(note_view._elided_text_layout))
            # Every line is a tuple of (text, rect)
            # We'll convert it to just a list of texts
            cache['text_layout_data']['lines'] = [
                line[0] for line in cache['text_layout_data']['lines'] if line
            ]

            if hasattr(note_view_state, 'text'):  # Probably unnecessary
                note_text = note_view_state.text
            else:
                note_text = ''
            cache['text_layout_data']['alignment'] = ('\n' in note_text)

        note_dict['cache'] = cache
        note_dicts_by_id[note.id] = note_dict

        # - Media link mapping per page update
        # (for local/internal files)
        # Move the image to the static folder for the page
        static_media_path = page_exp_folder / 'media'
        static_media_path.mkdir(parents=True, exist_ok=True)
        if hasattr(note, 'local_image_url'):
            local_image_url: Url = note.local_image_url
            if local_image_url.is_internal():
                path = desktop_app.media_store().path_for_internal_uri(
                    local_image_url)
            else:
                path = Path(local_image_url.path)

            if path.exists():
                new_path: Path = static_media_path / path.name
                if new_path.exists():  # Duplicate file names
                    new_name = f'{path.stem}_{uuid.uuid4()}{path.suffix}'
                    new_path = static_media_path / new_name
                shutil.copy(path, new_path)
                relative_path = new_path.relative_to(export_folder)
                image_url = Path('/') / relative_path.as_posix()
                note_dict['content']['image_url'] = str(image_url)

            # Hide the local image url
            note_dict['content'].pop('local_image_url', None)

    # - Arrow control points, etc
    arrow_dicts_by_id = {}
    for arrow_view in page_view.arrow_views():
        arrow = arrow_view.state().get_arrow()
        arrow_dict = dump_to_dict(arrow)

        cache = {}
        cache['curves'] = []
        for curve in arrow_view._cached_curves:
            points = [p.as_tuple() for p in curve]
            cache['curves'].append(points)
        arrow_dict['cache'] = cache
        arrow_dicts_by_id[arrow.id] = arrow_dict

    # add page to the /pages.json (or whatever). Should be a list.
    pages_json_path = export_folder / 'pages.json'
    if pages_json_path.exists():
        pages_json = json.loads(pages_json_path.read_text())
    else:
        pages_json = []

    for page_json in pages_json:
        if page_json['id'] == page_state['id']:
            pages_json.remove(page_json)
            break

    pages_json.append(page_state)
    pages_json_path.write_text(json.dumps(pages_json, indent=4))

    # # Write the notes.json
    # notes_json_path = page_exp_folder / 'notes.json'
    # notes_list = list(note_dicts_by_id.values())
    # notes_json_path.write_text(json.dumps(notes_list, indent=4))

    # # Write the arrows.json
    # arrows_json_path = page_exp_folder / 'arrows.json'
    # arrows_list = list(arrow_dicts_by_id.values())
    # arrows_json_path.write_text(json.dumps(arrows_list, indent=4))

    # Write to children.json
    children_json_path = page_exp_folder / 'children.json'
    notes_list = list(note_dicts_by_id.values())
    arrows_list = list(arrow_dicts_by_id.values())
    children_json = {
        'notes': notes_list,
        'arrows': arrows_list,
    }
    children_json_path.write_text(json.dumps(children_json, indent=4))

    # Have you checked for private notes + to bundle static files set the
    # web build folder in the user config
    def hackily_show_info_and_open_folder_if_ok():
        dialog_text = f"""
        <p>Exported to <b>{export_folder}</b>
        (User settings: static_export_folder)</p>
        <p>If you don't have them already - download the static files from
        <a href="https://pamet.misli.org/latest_build.zip">here</a>
        and place them in the export folder.</p>
        <br>
        <p>Open the export folder?</p>
        """
        open_folder = QMessageBox.question(None,
                                           'Exported',
                                           dialog_text,
                                           QMessageBox.Open
                                           | QMessageBox.Cancel,
                                           defaultButton=QMessageBox.Cancel)
        if open_folder == QMessageBox.Open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(export_folder)))

    QTimer.singleShot(100, hackily_show_info_and_open_folder_if_ok)


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


@command(title='Open page backups folder')
def open_page_backups_folder():
    tab_view, page_view = current_tab_and_page_views()
    page_id = page_view.state().id
    backup_service = pamet.desktop_app.backup_service()

    if not backup_service:
        QMessageBox.warning(
            page_view, 'No backups',
            ('Backup service not available. Have you enabled it '
             'in the user settings?'))
        return

    page_backups_folder = backup_service.page_backup_folder(page_id)

    if not page_backups_folder.exists():
        QMessageBox.warning(page_view, 'No backups',
                            'No backups folder present for this page')
        return

    path = Path(page_backups_folder)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


@command(title='Open repository folder')
def open_repository_folder():
    repo = pamet.sync_repo()
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(repo.path)))
