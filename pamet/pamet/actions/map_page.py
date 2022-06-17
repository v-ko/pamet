from __future__ import annotations
from typing import List

import misli
from misli import gui
import pamet

from misli.basic_classes import Point2D
from misli.gui.actions_library import action
from pamet.actions.note import abort_editing_note, create_new_note
from pamet.actions.note import finish_editing_note, start_editing_note
from pamet.helpers import snap_to_grid
from pamet.model import Note, Page
from pamet.actions import tab as tab_actions
from pamet.views.map_page.properties_widget import MapPagePropertiesViewState
from pamet.views.map_page.view import MapPageViewState
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.views.note.base_note_view import NoteViewState

log = misli.get_logger(__name__)


@action('map_page.start_mouse_drag_navigation')
def start_mouse_drag_navigation(map_page_view_id: str, mouse_position: Point2D,
                                first_delta: Point2D):

    map_page_view_state = gui.view_state(map_page_view_id)

    map_page_view_state.drag_navigation_active = True
    map_page_view_state.drag_navigation_start_position = mouse_position
    map_page_view_state.viewport_position_on_press = \
        map_page_view_state.viewport_center

    gui.update_state(map_page_view_state)
    mouse_drag_navigation_move(map_page_view_id, first_delta)


def mouse_drag_navigation_move(map_page_view_id: str, mouse_delta: Point2D):
    map_page_view_state = gui.view_state(map_page_view_id)

    unprojected_delta = (mouse_delta /
                         map_page_view_state.height_scale_factor())
    new_viewport_center: Point2D = (
        map_page_view_state.viewport_position_on_press + unprojected_delta)

    change_viewport_center(map_page_view_id, new_viewport_center.as_tuple())


@action('map_page.change_viewport_center')
def change_viewport_center(map_page_view_id: str,
                           new_viewport_center: Point2D):

    map_page_view_state = gui.view_state(map_page_view_id)

    map_page_view_state.viewport_center = Point2D(*new_viewport_center)
    gui.update_state(map_page_view_state)


@action('map_page.stop_drag_navigation')
def stop_drag_navigation(map_page_view_id: str):

    map_page_view_state = gui.view_state(map_page_view_id)
    map_page_view_state.drag_navigation_active = False
    gui.update_state(map_page_view_state)


@action('map_page.update_note_selections')
def update_note_selections(map_page_view_state: MapPageViewState,
                           selection_updates_by_note_id: dict):

    if not selection_updates_by_note_id:
        return

    selection_update_count = 0

    for note_id, selected in selection_updates_by_note_id.items():

        if note_id in map_page_view_state.selected_nc_ids and not selected:
            map_page_view_state.selected_nc_ids.remove(note_id)
            selection_update_count += 1

        elif note_id not in map_page_view_state.selected_nc_ids and selected:
            map_page_view_state.selected_nc_ids.add(note_id)
            selection_update_count += 1

        else:
            log.warning('Redundant entry in selection_updates_by_note_id')

    if selection_update_count > 0:
        gui.update_state(map_page_view_state)
        # log.info('Updated %s selections' % selection_update_count)
    else:
        log.info('No selections updated out of %s' %
                 selection_updates_by_note_id)


@action('map_page.clear_note_selection')
def clear_note_selection(map_page_view_state: str):
    selection_updates = {}
    for sc_id in map_page_view_state.selected_nc_ids:
        selection_updates[sc_id] = False

    if not selection_updates:
        return

    update_note_selections(map_page_view_state, selection_updates)


@action('map_page.set_viewport_height')
def set_viewport_height(map_page_view_id: str, new_height: float):
    map_page_view_state = gui.view_state(map_page_view_id)
    map_page_view_state.viewport_height = new_height

    gui.update_state(map_page_view_state)
    # //glutPostRedisplay(); artefact, thank you for siteseeing


@action('map_page.start_drag_select')
def start_drag_select(map_page_view_id: str, position: Point2D):
    map_page_view_state = gui.view_state(map_page_view_id)

    map_page_view_state.mouse_position_on_drag_select_start = Point2D(
        *position)
    map_page_view_state.drag_select_active = True
    gui.update_state(map_page_view_state)


@action('map_page.update_drag_select')
def update_drag_select(map_page_view_id: str,
                       rect_props: list,
                       drag_selected_nc_ids: list = None):

    map_page_view_state = gui.view_state(map_page_view_id)

    if drag_selected_nc_ids is None:
        drag_selected_nc_ids = []

    map_page_view_state.drag_select_rect_props = rect_props
    map_page_view_state.drag_selected_nc_ids.clear()

    for nc_id in drag_selected_nc_ids:
        if nc_id not in map_page_view_state.drag_selected_nc_ids:
            map_page_view_state.drag_selected_nc_ids.append(nc_id)

    gui.update_state(map_page_view_state)


@action('map_page.stop_drag_select')
def stop_drag_select(map_page_view_id: str):
    map_page_view_state = gui.view_state(map_page_view_id)

    map_page_view_state.drag_select_active = False
    map_page_view_state.selected_nc_ids.update(
        map_page_view_state.drag_selected_nc_ids)
    map_page_view_state.drag_selected_nc_ids.clear()
    map_page_view_state.drag_select_rect_props = [0, 0, 0, 0]

    gui.update_state(map_page_view_state)


@action('map_page.delete_selected_notes')
def delete_selected_notes(map_page_view_state: MapPageViewState):
    for nc_id in map_page_view_state.selected_nc_ids:
        ncs = gui.view_state(nc_id)
        # if not ncs:
        pamet.remove_note(ncs.get_note())

    map_page_view_state.selected_nc_ids.clear()
    misli.gui.update_state(map_page_view_state)


@action('map_page.start_notes_resize')
def start_notes_resize(map_page_view_id: str, main_note: Note,
                       mouse_position: Point2D,
                       resize_circle_center_projected: Point2D):

    map_page_view_state = gui.view_state(map_page_view_id)

    map_page_view_state.note_resize_delta_from_note_edge = (
        resize_circle_center_projected - mouse_position)
    map_page_view_state.note_resize_click_position = mouse_position
    map_page_view_state.note_resize_main_note = main_note.copy()

    map_page_view_state.note_resize_active = True
    gui.update_state(map_page_view_state)


@action('map_page.resize_note_views')
def resize_note_views(new_size: Point2D, nc_ids: list):
    for nc_id in nc_ids:
        ncs = gui.view_state(nc_id)

        ncs.set_size(new_size)
        gui.update_state(ncs)


@action('map_page.resize_notes')
def resize_notes(new_size: Point2D, notes: List[Note]):
    for note in notes:
        note.set_size(new_size)
        pamet.update_note(note)


@action('map_page.stop_notes_resize')
def stop_notes_resize(map_page_view_id: str, new_size: list, nc_ids: list):

    map_page_view_state = gui.view_state(map_page_view_id)
    map_page_view_state.note_resize_active = False

    # page = map_page_view_state.page
    notes = [gui.view_state(nc_id).get_note() for nc_id in nc_ids]
    resize_notes(new_size, notes)

    gui.update_state(map_page_view_state)


@action('map_page.start_note_drag')
def start_note_drag(map_page_view_id: str, mouse_pos: list):
    map_page_view_state = gui.view_state(map_page_view_id)
    if map_page_view_state.drag_select_active:
        stop_drag_select(map_page_view_id)

    map_page_view_state = gui.view_state(map_page_view_id)
    map_page_view_state.mouse_position_on_note_drag_start = Point2D(*mouse_pos)
    map_page_view_state.note_drag_active = True
    gui.update_state(map_page_view_state)


@action('map_page.note_drag_nc_position_update')
def note_drag_nc_position_update(nc_ids: list, delta: Point2D):
    for nc_id in nc_ids:
        ncs: NoteViewState = gui.view_state(nc_id)

        rect = ncs.get_note().rect()
        rect.move_top_left(snap_to_grid(rect.top_left() + delta))
        ncs.set_rect(rect)

        gui.update_state(ncs)


@action('map_page.stop_note_drag')
def stop_note_drag(map_page_view_id: str, nc_ids: list, delta: list):
    map_page_view_state = gui.view_state(map_page_view_id)

    d = Point2D(*delta)
    for nc_id in nc_ids:
        ncs = gui.view_state(nc_id)
        note = ncs.get_note()

        note.x += d.x()
        note.y += d.y()

        pamet.update_note(note)

    map_page_view_state.note_drag_active = False
    gui.update_state(map_page_view_state)


@action('map_page.select_all_notes')
def select_all_notes(map_page_view_id):
    map_page_view_state = gui.view_state(map_page_view_id)

    for nc in gui.view_children(map_page_view_id):
        map_page_view_state.selected_nc_ids.add(nc.id)

    gui.update_state(map_page_view_state)


@action('map_page.resize_page')
def resize_page(map_page_view_id, width, height):
    map_page_view_state = gui.view_state(map_page_view_id)
    map_page_view_state.geometry.set_size(width, height)
    gui.update_state(map_page_view_state)


@action('notes.color_selected_notes')
def color_selected_notes(map_page_view_state: str,
                         color: list = None,
                         background_color: list = None):
    for note_view_id in map_page_view_state.selected_nc_ids:
        note = gui.view_state(note_view_id).get_note()

        color = color or note.color
        background_color = background_color or note.background_color

        note.color = color
        note.background_color = background_color
        pamet.update_note(note)

    map_page_view_state.selected_nc_ids.clear()
    misli.gui.update_state(map_page_view_state)


@action('map_page.open_page_properties')
def open_page_properties(tab_state: TabViewState, focused_prop: str = None):
    page_view_state = tab_state.page_view_state

    properties_view_state = MapPagePropertiesViewState(
        page_id=page_view_state.page.id)

    misli.gui.add_state(properties_view_state)

    if focused_prop:
        properties_view_state.focused_prop = focused_prop
        misli.gui.update_state(properties_view_state)

    tab_state.right_sidebar_state = properties_view_state
    tab_state.right_sidebar_visible = True
    tab_state.page_properties_open = True

    misli.gui.update_state(tab_state)


@action('map_page.save_page_properties')
def save_page_properties(page: Page):
    pamet.update_page(page)


# @action('map_page.close_page_properties')
# def close_page_properties(tab_state: TabViewState):
#     tab_state.right_sidebar_visible = False
#     tab_state.right_sidebar_view_id = None

#     misli.gui.update_state(tab_state)


@action('map_page.delete_page')
def delete_page(tab_view_state, page):
    pamet.remove_page(page)
    next_page = pamet.helpers.get_default_page()
    if not next_page:
        raise NotImplementedError
        # misli.gui.create_view(
        #     parentdsdid=tab_view_state,
        #     view_class_metadata_filter=dict(name='MessageBox'),
        #     init_kwargs=dict(title='Info',
        #                      text=('You deleted the last page. '
        #                            'A blank one has been created for you')))
        next_page = pamet.actions.other.create_default_page()
    tab_actions.tab_go_to_page(tab_view_state, next_page)


@action('map_page.switch_note_type')
def switch_note_type(tab_state: TabViewState, note: Note):
    if tab_state.edit_view_state.create_mode:
        abort_editing_note(tab_state)
        create_new_note(tab_state, note)
    else:
        finish_editing_note(tab_state, note)
        start_editing_note(tab_state, note)


@action('map_page.handle_note_added')
def handle_note_added(page_view_state: MapPageViewState, note: Note):
    ViewType = pamet.note_view_type(note_type_name=type(note).__name__,
                                    edit=False)
    StateType = pamet.note_state_type_by_view(ViewType.__name__)
    nv_state = StateType(**note.asdict(), note_gid=note.gid())
    misli.gui.add_state(nv_state)
    page_view_state.note_view_states.append(nv_state)
    misli.gui.update_state(page_view_state)


@action('map_page.handle_note_removed')
def handle_note_removed(page_view_state: MapPageViewState, note: Note):
    nv_states = filter(lambda x: x.note_gid == note.gid(),
                       page_view_state.note_view_states)
    for nv_state in nv_states:  # Should be len==1
        misli.gui.remove_state(nv_state)
        page_view_state.note_view_states.remove(nv_state)
    misli.gui.update_state(page_view_state)


@action('map_page.handle_note_updated')
def handle_note_updated(note_view_state: NoteViewState, note: Note):
    note_view_state.update_from_note(note)
    misli.gui.update_state(note_view_state)


@action('map_page.handle_page_name_updated')
def handle_page_name_updated(tab_view_state: TabViewState, page: Page):
    tab_view_state.title = page.name
    misli.gui.update_state(tab_view_state)
