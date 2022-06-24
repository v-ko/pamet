from __future__ import annotations
from copy import copy
from dataclasses import fields
from typing import List

import misli
from misli import gui
from misli.entity_library.entity import Entity
from numpy import isin
import pamet

from misli.basic_classes import Point2D
from misli.gui.actions_library import action
from pamet.actions.note import abort_editing_note, create_new_note
from pamet.actions.note import finish_editing_note, start_editing_note
from pamet.helpers import snap_to_grid
from pamet.model import Note, Page
from pamet.actions import tab as tab_actions
from pamet.model.arrow import Arrow
from pamet.views.arrow.widget import ArrowView, ArrowViewState
from pamet.views.map_page.properties_widget import MapPagePropertiesViewState
from pamet.views.map_page.state import MapPageViewState, MapPageMode
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.views.note.base_note_view import NoteView, NoteViewState

log = misli.get_logger(__name__)


@action('map_page.start_mouse_drag_navigation')
def start_mouse_drag_navigation(map_page_view_state: MapPageViewState,
                                mouse_position: Point2D, first_delta: Point2D):
    map_page_view_state.set_mode(MapPageMode.DRAG_NAVIGATION)
    # map_page_view_state.drag_navigation_active = True
    map_page_view_state.drag_navigation_start_position = mouse_position
    map_page_view_state.viewport_position_on_press = \
        map_page_view_state.viewport_center

    gui.update_state(map_page_view_state)
    mouse_drag_navigation_move(map_page_view_state, first_delta)


def mouse_drag_navigation_move(map_page_view_state: MapPageViewState,
                               mouse_delta: Point2D):
    unprojected_delta = (mouse_delta /
                         map_page_view_state.height_scale_factor())
    new_viewport_center: Point2D = (
        map_page_view_state.viewport_position_on_press + unprojected_delta)

    change_viewport_center(map_page_view_state, new_viewport_center.as_tuple())


@action('map_page.change_viewport_center')
def change_viewport_center(map_page_view_state: MapPageViewState,
                           new_viewport_center: Point2D):

    map_page_view_state.viewport_center = Point2D(*new_viewport_center)
    gui.update_state(map_page_view_state)


@action('map_page.stop_drag_navigation')
def stop_drag_navigation(map_page_view_state: MapPageViewState):
    # map_page_view_state.drag_navigation_active = False
    map_page_view_state.set_mode(MapPageMode.NONE)
    gui.update_state(map_page_view_state)


@action('map_page.update_note_selections')
def update_child_selections(map_page_view_state: MapPageViewState,
                            selection_updates_by_child_id: dict):

    if not selection_updates_by_child_id:
        return

    selection_update_count = 0
    for child_id, selected in selection_updates_by_child_id.items():

        if (child_id in map_page_view_state.selected_child_ids
                and not selected):
            map_page_view_state.selected_child_ids.remove(child_id)
            selection_update_count += 1

        elif (child_id not in map_page_view_state.selected_child_ids
              and selected):
            map_page_view_state.selected_child_ids.add(child_id)
            selection_update_count += 1

        else:
            log.warning('Redundant entry in selection_updates_by_note_id')

    if selection_update_count > 0:
        gui.update_state(map_page_view_state)
        # log.info('Updated %s selections' % selection_update_count)
    else:
        log.info('No selections updated out of %s' %
                 selection_updates_by_child_id)


@action('map_page.clear_note_selection')
def clear_note_selection(map_page_view_state: str):
    selection_updates = {}
    for selected_child in map_page_view_state.selected_child_ids:
        selection_updates[selected_child] = False

    if not selection_updates:
        return

    update_child_selections(map_page_view_state, selection_updates)


@action('map_page.set_viewport_height')
def set_viewport_height(map_page_view_state: MapPageViewState,
                        new_height: float):
    map_page_view_state.viewport_height = new_height

    gui.update_state(map_page_view_state)
    # //glutPostRedisplay(); artefact, thank you for siteseeing


@action('map_page.start_drag_select')
def start_drag_select(map_page_view_state: MapPageViewState,
                      position: Point2D):
    map_page_view_state.set_mode(MapPageMode.DRAG_SELECT)
    map_page_view_state.mouse_position_on_drag_select_start = Point2D(
        *position)

    # map_page_view_state.drag_select_active = True
    gui.update_state(map_page_view_state)


@action('map_page.update_drag_select')
def update_drag_select(map_page_view_state: MapPageViewState,
                       rect_props: list,
                       drag_selected_child_ids: list = None):
    if drag_selected_child_ids is None:
        drag_selected_child_ids = []

    map_page_view_state.drag_select_rect_props = rect_props
    map_page_view_state.drag_selected_child_ids.clear()

    for nc_id in drag_selected_child_ids:
        if nc_id not in map_page_view_state.drag_selected_child_ids:
            map_page_view_state.drag_selected_child_ids.append(nc_id)

    gui.update_state(map_page_view_state)


@action('map_page.stop_drag_select')
def stop_drag_select(map_page_view_state: MapPageViewState):
    map_page_view_state.selected_child_ids.update(
        map_page_view_state.drag_selected_child_ids)
    map_page_view_state.clear_mode()

    gui.update_state(map_page_view_state)


@action('map_page.delete_selected_notes')
def delete_selected_notes(map_page_view_state: MapPageViewState):
    arrow_gids_for_removal = set()

    # Delete the notes and store the arrows in the list
    for nc_id in map_page_view_state.selected_child_ids:
        child_state = gui.view_state(nc_id)
        if isinstance(child_state, NoteViewState):
            pamet.remove_note(child_state.get_note())
        elif isinstance(child_state, ArrowViewState):
            arrow_gids_for_removal.add(child_state.arrow_gid)
        else:
            raise Exception('Unexpected state type')

    # Mark for removal the arrows that are anchored on any of the seleced notes
    for arrow_state in map_page_view_state.arrow_view_states:
        if ((arrow_state.tail_note_id and arrow_state.tail_note_id
             in map_page_view_state.selected_child_ids)
                or (arrow_state.head_note_id and arrow_state.head_note_id
                    in map_page_view_state.selected_child_ids)):
            arrow_gids_for_removal.add(arrow_state.arrow_gid)

    # Delete the arrows
    for arrow_gid in arrow_gids_for_removal:
        pamet.remove_arrow(pamet.find_one(gid=arrow_gid))

    map_page_view_state.selected_child_ids.clear()
    misli.gui.update_state(map_page_view_state)


@action('map_page.start_notes_resize')
def start_notes_resize(map_page_view_state: MapPageViewState, main_note: Note,
                       mouse_position: Point2D,
                       resize_circle_center_projected: Point2D):
    map_page_view_state.set_mode(MapPageMode.NOTE_RESIZE)
    map_page_view_state.note_resize_delta_from_note_edge = (
        resize_circle_center_projected - mouse_position)
    map_page_view_state.note_resize_click_position = mouse_position
    map_page_view_state.note_resize_main_note = main_note.copy()

    for child_id in map_page_view_state.selected_child_ids:
        child_state = misli.gui.view_state(child_id)
        if isinstance(child_state, NoteViewState):
            map_page_view_state.note_resize_states.append(child_state)

    # map_page_view_state.note_resize_active = True
    gui.update_state(map_page_view_state)


@action('map_page.resize_note_views')
def resize_note_views(map_page_view_state: MapPageViewState,
                      new_size: Point2D):
    for ncs in map_page_view_state.note_resize_states:
        ncs.set_size(new_size)
        gui.update_state(ncs)


@action('map_page.finish_notes_resize')
def finish_notes_resize(map_page_view_state: MapPageViewState, new_size: list):
    for note_state in map_page_view_state.note_resize_states:
        note = note_state.get_note()
        note.set_size(new_size)
        pamet.update_note(note)
    map_page_view_state.clear_mode()

    gui.update_state(map_page_view_state)


@action('map_page.start_child_move')
def start_child_move(map_page_view_state: MapPageViewState, mouse_pos: list):
    map_page_view_state.set_mode(MapPageMode.NOTE_MOVE)
    map_page_view_state.mouse_position_on_note_drag_start = Point2D(*mouse_pos)
    for cid in map_page_view_state.selected_child_ids:
        child_state = misli.gui.view_state(cid)
        if isinstance(child_state, ArrowViewState):
            map_page_view_state.moved_arrow_states.append(child_state)
        elif isinstance(child_state, NoteViewState):
            map_page_view_state.moved_note_states.append(child_state)
        else:
            raise Exception('Unexpected state type')

    gui.update_state(map_page_view_state)


@action('map_page.moved_child_view_update')
def moved_child_view_update(map_page_view_state: MapPageViewState,
                            delta: Point2D):
    for note_state in map_page_view_state.moved_note_states:
        rect = note_state.get_note().rect()
        rect.move_top_left(snap_to_grid(rect.top_left() + delta))
        note_state.set_rect(rect)
        gui.update_state(note_state)

    for arrow_state in map_page_view_state.moved_arrow_states:
        arrow = arrow_state.get_arrow()
        if arrow.tail_point:
            arrow_state.tail_point = snap_to_grid(arrow.tail_point + delta)
        if arrow.head_point:
            arrow_state.head_point = snap_to_grid(arrow.head_point + delta)
        gui.update_state(arrow_state)


@action('map_page.finish_child_move')
def finish_child_move(map_page_view_state: MapPageViewState, delta: Point2D):
    for note_state in map_page_view_state.moved_note_states:
        note = note_state.get_note()
        note.x = snap_to_grid(note.x + delta.x())
        note.y = snap_to_grid(note.y + delta.y())
        pamet.update_note(note)

    for arrow_state in map_page_view_state.moved_arrow_states:
        arrow = arrow_state.get_arrow()
        if arrow.tail_point:
            arrow.tail_point = snap_to_grid(arrow.tail_point + delta)
        if arrow.head_point:
            arrow.head_point = snap_to_grid(arrow.head_point + delta)
        pamet.update_arrow(arrow)

    map_page_view_state.clear_mode()
    gui.update_state(map_page_view_state)


@action('map_page.select_all_notes')
def select_all_notes(map_page_view_id):
    map_page_view_state = gui.view_state(map_page_view_id)

    for nc in gui.view_children(map_page_view_id):
        map_page_view_state.selected_child_ids.add(nc.id)

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
    for note_view_id in map_page_view_state.selected_child_ids:
        note = gui.view_state(note_view_id).get_note()

        color = color or note.color
        background_color = background_color or note.background_color

        note.color = color
        note.background_color = background_color
        pamet.update_note(note)

    map_page_view_state.selected_child_ids.clear()
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


@action('map_page.handle_child_added')
def handle_child_added(page_view_state: MapPageViewState, child: Entity):
    if isinstance(child, Note):
        ViewType = pamet.note_view_type(note_type_name=type(child).__name__,
                                        edit=False)
        StateType = pamet.note_state_type_by_view(ViewType.__name__)
        nv_state = StateType(**child.asdict(), note_gid=child.gid())
        misli.gui.add_state(nv_state)
        page_view_state.note_view_states.append(nv_state)
    elif isinstance(child, Arrow):
        arrow_view_state = ArrowViewState(**child.asdict(),
                                          arrow_gid=child.gid())
        misli.gui.add_state(arrow_view_state)
        page_view_state.arrow_view_states.append(arrow_view_state)

    misli.gui.update_state(page_view_state)


@action('map_page.handle_child_removed')
def handle_child_removed(page_view_state: MapPageViewState, child: Entity):
    if isinstance(child, Note):
        nv_states = filter(lambda x: x.note_gid == child.gid(),
                           page_view_state.note_view_states)
        for nv_state in nv_states:  # Should be len==1
            misli.gui.remove_state(nv_state)
            page_view_state.note_view_states.remove(nv_state)
    elif isinstance(child, Arrow):
        av_states = filter(lambda x: x.arrow_gid == child.gid(),
                           page_view_state.arrow_view_states)
        for nv_state in av_states:  # Should be len==1
            misli.gui.remove_state(nv_state)
            page_view_state.arrow_view_states.remove(nv_state)

    misli.gui.update_state(page_view_state)


@action('map_page.handle_child_updated')
def handle_child_updated(child_view_state: NoteViewState, child: Note):
    if isinstance(child, Note):
        child_view_state.update_from_note(child)
    elif isinstance(child, Arrow):
        child_view_state.update_from_arrow(child)
    misli.gui.update_state(child_view_state)


@action('map_page.handle_page_name_updated')
def handle_page_name_updated(tab_view_state: TabViewState, page: Page):
    tab_view_state.title = page.name
    misli.gui.update_state(tab_view_state)


@action('map_page.start_arrow_creation')
def start_arrow_creation(map_page_view_state: MapPageViewState):
    av_state = ArrowViewState(page_id=map_page_view_state.page_id)
    misli.gui.add_state(av_state)

    map_page_view_state.set_mode(MapPageMode.CREATE_ARROW)
    map_page_view_state.new_arrow_view_states.append(av_state)
    misli.gui.update_state(map_page_view_state)


@action('map_page.abort_special_mode')
def abort_special_mode(map_page_view_state: MapPageViewState):
    # Reset the manipulated views
    for note_state in map_page_view_state.moved_note_states:
        note_state.update_from_note(note_state.get_note())
        misli.gui.update_state(note_state)

    for arrow_state in map_page_view_state.moved_arrow_states:
        arrow_state.update_from_arrow(arrow_state.get_arrow())
        misli.gui.update_state(arrow_state)

    for note_state in map_page_view_state.note_resize_states:
        note_state.update_from_note(note_state.get_note())
        misli.gui.update_state(note_state)

    map_page_view_state.clear_mode()
    misli.gui.update_state(map_page_view_state)


@action('map_page.place_arrow_tail')
def place_arrow_tail(arrow_view_state: ArrowViewState,
                     real_pos: Point2D,
                     anchor: str = None):
    if anchor:
        arrow_view_state.tail_anchor = anchor
    else:
        arrow_view_state.tail_point = real_pos

    misli.gui.update_state(arrow_view_state)


@action('map_page.place_arrow_head')
def place_arrow_head(arrow_view_state: ArrowViewState,
                     real_pos: Point2D,
                     anchor: str = None):
    if anchor:
        arrow_view_state.head_anchor = anchor
    else:
        arrow_view_state.head_point = real_pos

    misli.gui.update_state(arrow_view_state)


@action('map_page.arrow_creation_click')
def arrow_creation_click(map_page_view_state: MapPageViewState,
                         real_pos: Point2D,
                         anchor: str = None):
    # arrow_vs = ArrowViewState()
    should_finish = False

    for arrow_vs in map_page_view_state.new_arrow_view_states:
        if not (arrow_vs.tail_anchor or arrow_vs.tail_point):
            place_arrow_tail(arrow_vs, real_pos, anchor)
            if should_finish:
                raise Exception(
                    'Some of the arrows have tails while others don\'t')
        else:
            place_arrow_head(arrow_vs, real_pos, anchor)
            should_finish = True

    if should_finish:
        finish_arrow_creation(map_page_view_state)


@action('map_page.arrow_creation_move')
def arrow_creation_move(map_page_view_state, real_pos):
    for av_state in map_page_view_state.new_arrow_view_states:
        place_arrow_head(av_state, real_pos)


@action('map_page.finish_arrow_creation')
def finish_arrow_creation(map_page_view_state):
    for arrow_vs in map_page_view_state.new_arrow_view_states:
        # If both ends of the arrow are at the same point - cancel it
        if arrow_vs.tail_point and arrow_vs.head_point:
            if arrow_vs.tail_point == arrow_vs.head_point:
                continue
        if arrow_vs.tail_anchor and arrow_vs.head_anchor:
            if arrow_vs.tail_anchor == arrow_vs.head_anchor:
                continue

        # Get the properties for the new arrow from the view state
        arrow = Arrow(page_id=arrow_vs.page_id)
        for field in fields(Arrow):
            value = getattr(arrow_vs, field.name)
            setattr(arrow, field.name, value)

        pamet.insert_arrow(arrow)

    map_page_view_state.clear_mode()
    misli.gui.update_state(map_page_view_state)
