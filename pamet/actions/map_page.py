from __future__ import annotations
from typing import List

import fusion
from fusion import fsm
from fusion.libs.entity import Entity, get_entity_id
import pamet

from fusion.util import Point2D, Rectangle
from fusion.libs.action import action
from pamet.constants import ALIGNMENT_GRID_UNIT
from pamet.util import snap_to_grid
from pamet.util.url import Url
from pamet.model.page import Page
from pamet.model.note import Note
from pamet.actions import tab as tab_actions
from pamet.model.arrow import Arrow, ArrowAnchorType
from pamet.model.card_note import CardNote
from pamet.model.image_note import ImageNote
from pamet.model.text_note import TextNote
from pamet.views.arrow.widget import ArrowViewState
from pamet.views.map_page.properties_widget import MapPagePropertiesViewState
from pamet.views.map_page.state import MapPageMode, MapPageViewState
from pamet.views.note.base.state import NoteViewState
from pamet.views.note.qt_helpers import minimal_nonelided_size

log = fusion.get_logger(__name__)


@action('map_page.start_mouse_drag_navigation')
def start_mouse_drag_navigation(map_page_view_state: MapPageViewState,
                                mouse_position: Point2D, first_delta: Point2D):
    map_page_view_state.set_mode(MapPageMode.DRAG_NAVIGATION)
    map_page_view_state.drag_navigation_start_position = mouse_position
    map_page_view_state.viewport_position_on_press = \
        map_page_view_state.viewport_center

    fsm.update_state(map_page_view_state)
    mouse_drag_navigation_move(map_page_view_state, first_delta)


@action('map_page.mouse_drag_navigation_move')
def mouse_drag_navigation_move(map_page_view_state: MapPageViewState,
                               mouse_delta: Point2D):
    unprojected_delta = (mouse_delta /
                         map_page_view_state.height_scale_factor())
    new_viewport_center: Point2D = (
        map_page_view_state.viewport_position_on_press + unprojected_delta)

    map_page_view_state.viewport_center = new_viewport_center
    fsm.update_state(map_page_view_state)


@action('map_page.finish_mouse_drag_navigation')
def finish_mouse_drag_navigation(map_page_view_state: MapPageViewState):
    map_page_view_state.set_mode(MapPageMode.NONE)
    fsm.update_state(map_page_view_state)


@action('map_page.update_note_selections')
def update_child_selections(map_page_view_state: MapPageViewState,
                            selection_updates_by_child: dict):

    if not selection_updates_by_child:
        return

    selection_update_count = 0
    for child, selected in selection_updates_by_child.items():

        if (child in map_page_view_state.selected_children and not selected):
            map_page_view_state.selected_children.remove(child)
            selection_update_count += 1

        elif (child not in map_page_view_state.selected_children and selected):
            map_page_view_state.selected_children.add(child)
            selection_update_count += 1

        else:
            log.warning('Redundant entry in selection_updates_by_note_id')

    # If there's only one arrow selected - show its control points
    single_selected_arrow = None
    if len(map_page_view_state.selected_children) == 1:
        (first_selected_child, ) = map_page_view_state.selected_children
        for arrow_vs in map_page_view_state.arrow_view_states:
            if arrow_vs.id == first_selected_child.id:
                single_selected_arrow = arrow_vs

    if single_selected_arrow:
        map_page_view_state.arrow_with_visible_cps = single_selected_arrow
    else:
        map_page_view_state.arrow_with_visible_cps = None

    if selection_update_count > 0:
        fsm.update_state(map_page_view_state)
        # log.info('Updated %s selections' % selection_update_count)
    else:
        log.info('No selections updated out of %s' %
                 selection_updates_by_child)


@action('map_page.clear_child_selection')
def clear_child_selection(map_page_view_state: str):
    selection_updates = {}
    for selected_child in map_page_view_state.selected_children:
        selection_updates[selected_child] = False

    if not selection_updates:
        return

    update_child_selections(map_page_view_state, selection_updates)


@action('map_page.set_viewport_height')
def set_viewport_height(map_page_view_state: MapPageViewState,
                        new_height: float):
    map_page_view_state.viewport_height = new_height
    fsm.update_state(map_page_view_state)
    # //glutPostRedisplay(); artefact, thank you for siteseeing


@action('map_page.start_drag_select')
def start_drag_select(map_page_view_state: MapPageViewState,
                      position: Point2D):
    map_page_view_state.set_mode(MapPageMode.DRAG_SELECT)
    map_page_view_state.mouse_position_on_drag_select_start = position
    # map_page_view_state.drag_selected_children.update(children_under_mouse)

    fsm.update_state(map_page_view_state)


@action('map_page.update_drag_select')
def update_drag_select(map_page_view_state: MapPageViewState,
                       rect_props: list,
                       drag_selected_children: set = None):
    if drag_selected_children is None:
        drag_selected_children = set()

    map_page_view_state.drag_select_rect_props = rect_props
    map_page_view_state.drag_selected_children.clear()

    for child_state in drag_selected_children:
        if child_state not in map_page_view_state.drag_selected_children:
            map_page_view_state.drag_selected_children.add(child_state)

    fsm.update_state(map_page_view_state)


@action('map_page.stop_drag_select')
def stop_drag_select(map_page_view_state: MapPageViewState, position: Point2D):
    added_selections = (map_page_view_state.drag_selected_children -
                        map_page_view_state.selected_children)
    removed_selections = map_page_view_state.selected_children.intersection(
        map_page_view_state.drag_selected_children)

    selection_updates = {child_state: True for child_state in added_selections}
    selection_updates.update(
        {child_state: False
         for child_state in removed_selections})

    # If there was no drag selection, but only a click

    update_child_selections(map_page_view_state, selection_updates)
    map_page_view_state.clear_mode()

    fsm.update_state(map_page_view_state)


@action('map_page.delete_notes_and_connected_arrows')
def delete_notes_and_connected_arrows(notes: List[Note]):
    if not notes:
        return

    note_ids = []
    page_id = None
    for note in notes:
        note_ids.append(note.own_id)
        if not page_id:
            page_id = note.page_id
        elif page_id != note.page_id:
            raise Exception

    arrows_for_deletion = []
    for arrow in pamet.arrows(pamet.page(note.page_id)):
        if (arrow.tail_note_id and arrow.tail_note_id in note_ids) or\
                (arrow.head_note_id and arrow.head_note_id in note_ids):
            arrows_for_deletion.append(arrow)

    for arrow in arrows_for_deletion:
        pamet.remove_arrow(arrow)

    for note in notes:
        pamet.remove_note(note)


@action('map_page.delete_selected_children')
def delete_selected_children(map_page_view_state: MapPageViewState):
    # Parse the ids into lists for removal, since we need to do it in order -
    # .. ?
    arrows_for_removal = []
    notes_for_removal = []
    for child_state in map_page_view_state.selected_children:
        if isinstance(child_state, NoteViewState):
            note = child_state.get_note()
            notes_for_removal.append(note)
        elif isinstance(child_state, ArrowViewState):
            arrows_for_removal.append(child_state.get_arrow())
        else:
            raise Exception('Unexpected state type')

    # Execute the removal
    for arrow in arrows_for_removal:
        pamet.remove_arrow(arrow)

    delete_notes_and_connected_arrows(notes_for_removal)

    clear_child_selection(map_page_view_state)
    fsm.update_state(map_page_view_state)


@action('map_page.start_notes_resize')
def start_notes_resize(map_page_view_state: MapPageViewState, main_note: Note,
                       mouse_position: Point2D,
                       resize_circle_center_projected: Point2D):
    map_page_view_state.set_mode(MapPageMode.NOTE_RESIZE)
    map_page_view_state.note_resize_delta_from_note_edge = (
        resize_circle_center_projected - mouse_position)
    map_page_view_state.note_resize_click_position = mouse_position
    map_page_view_state.note_resize_main_note = main_note.copy()

    for child_state in map_page_view_state.selected_children:
        if isinstance(child_state, NoteViewState):
            map_page_view_state.note_resize_states.append(child_state)

    # map_page_view_state.note_resize_active = True
    fsm.update_state(map_page_view_state)


@action('map_page.resize_note_views')
def resize_note_views(map_page_view_state: MapPageViewState,
                      new_size: Point2D):
    for ncs in map_page_view_state.note_resize_states:
        ncs.set_size(snap_to_grid(new_size))
        fsm.update_state(ncs)


@action('map_page.finish_notes_resize')
def finish_notes_resize(map_page_view_state: MapPageViewState, new_size: list):
    for note_state in map_page_view_state.note_resize_states:
        note = note_state.get_note()
        note.set_size(snap_to_grid(new_size))
        pamet.update_note(note)
    map_page_view_state.clear_mode()

    fsm.update_state(map_page_view_state)


@action('map_page.start_child_move')
def start_child_move(map_page_view_state: MapPageViewState,
                     mouse_pos: Point2D):
    map_page_view_state.set_mode(MapPageMode.CHILD_MOVE)
    map_page_view_state.mouse_position_on_note_drag_start = mouse_pos
    for child_state in map_page_view_state.selected_children:
        if isinstance(child_state, ArrowViewState):
            map_page_view_state.moved_arrow_states.append(child_state)
        elif isinstance(child_state, NoteViewState):
            map_page_view_state.moved_note_states.append(child_state)
        else:
            raise Exception('Unexpected state type')

    fsm.update_state(map_page_view_state)


@action('map_page.moved_child_view_update')
def moved_child_view_update(map_page_view_state: MapPageViewState,
                            delta: Point2D):
    moved_note_ids = []
    for note_state in map_page_view_state.moved_note_states:
        note = note_state.get_note()
        moved_note_ids.append(note.id)
        rect = note.rect()
        rect.set_top_left(snap_to_grid(rect.top_left() + delta))
        note_state.set_rect(rect)
        fsm.update_state(note_state)

    for arrow_state in map_page_view_state.moved_arrow_states:
        arrow: Arrow = arrow_state.get_arrow()
        if arrow.tail_point:
            arrow_state.tail_point = snap_to_grid(arrow.tail_point + delta)
        if arrow.head_point:
            arrow_state.head_point = snap_to_grid(arrow.head_point + delta)

        tail_moved = arrow.tail_point or arrow.tail_note_id in moved_note_ids
        head_moved = arrow.head_point or arrow.head_note_id in moved_note_ids
        if tail_moved and head_moved:
            mid_points = arrow.mid_points
            mid_points = [
                snap_to_grid(mid_point + delta) for mid_point in mid_points
            ]
            arrow_state.replace_midpoints(mid_points)

        fsm.update_state(arrow_state)


@action('map_page.finish_child_move')
def finish_child_move(map_page_view_state: MapPageViewState, delta: Point2D):
    moved_note_ids = []
    for note_state in map_page_view_state.moved_note_states:
        note = note_state.get_note()
        moved_note_ids.append(note.id)
        note.x = snap_to_grid(note.x + delta.x())
        note.y = snap_to_grid(note.y + delta.y())
        pamet.update_note(note)

    for arrow_state in map_page_view_state.moved_arrow_states:
        arrow = arrow_state.get_arrow()
        if arrow.tail_point:
            arrow.tail_point = snap_to_grid(arrow.tail_point + delta)
        if arrow.head_point:
            arrow.head_point = snap_to_grid(arrow.head_point + delta)

        tail_moved = arrow.tail_point or arrow.tail_note_id in moved_note_ids
        head_moved = arrow.head_point or arrow.head_note_id in moved_note_ids
        if tail_moved and head_moved:
            mid_points = arrow.mid_points
            mid_points = [
                snap_to_grid(mid_point + delta) for mid_point in mid_points
            ]
            arrow.replace_midpoints(mid_points)
        pamet.update_arrow(arrow)

    map_page_view_state.clear_mode()
    fsm.update_state(map_page_view_state)


@action('map_page.select_all_notes')
def select_all_notes(map_page_view_state: MapPageViewState):
    for note_vs in map_page_view_state.note_view_states:
        map_page_view_state.selected_children.add(note_vs)

    fsm.update_state(map_page_view_state)


@action('map_page.resize_page')
def resize_page(map_page_view_state: MapPageViewState, new_size: Point2D):
    map_page_view_state.geometry.set_size(new_size)
    fsm.update_state(map_page_view_state)


@action('notes.color_selected_children')
def color_selected_children(map_page_view_state: str,
                            color: list = None,
                            background_color: list = None):
    for child_state in map_page_view_state.selected_children:

        if isinstance(child_state, NoteViewState):
            note = child_state.get_note()

            color = color or note.color
            background_color = background_color or note.background_color

            note.color = color
            note.background_color = background_color
            pamet.update_note(note)

        elif isinstance(child_state, ArrowViewState):
            arrow = child_state.get_arrow()
            color = color or arrow.color
            arrow.color = color
            pamet.update_arrow(arrow)
        else:
            raise Exception

    clear_child_selection(map_page_view_state)
    fsm.update_state(map_page_view_state)


@action('map_page.open_page_properties')
def open_page_properties(tab_state: TabViewState, focused_prop: str = None):
    page_view_state = tab_state.page_view_state

    properties_view_state = MapPagePropertiesViewState(
        id=page_view_state.page_id)

    fsm.add_state(properties_view_state)

    if focused_prop:
        properties_view_state.focused_prop = focused_prop
        fsm.update_state(properties_view_state)

    tab_state.page_edit_view_state = properties_view_state

    fsm.update_state(tab_state)


@action('map_page.save_page_properties')
def save_page_properties(page: Page):
    pamet.update_page(page)


@action('map_page.delete_page')
def delete_page(tab_view_state: TabViewState, page: Page):
    pamet.remove_page(page)
    # Try to go to the last page if any
    next_page = None
    if tab_view_state.navigation_history:
        next_page = pamet.page(
            Url(tab_view_state.navigation_history[-1]).get_page_id())

    if not next_page:
        next_page = pamet.default_page() or pamet.sync_repo().find_one(
            type=Page)

    if not next_page:
        next_page = pamet.actions.other.create_default_page()
    tab_actions.go_to_url(tab_view_state, next_page.url())


@action('map_page.handle_child_added', issuer='entity_change_apply_logic')
def handle_child_added(page_view_state: MapPageViewState, child: Entity):
    if isinstance(child, Note):
        if page_view_state.view_state_for_note_own_id(child.own_id):
            return  # A workaround for duplicate calls.
            # These methods should be replaced by a PageUpdate service
            # (instead of per-page subscriptions, etc)
        ViewType = pamet.note_view_type(note_type_name=type(child).__name__,
                                        edit=False)
        StateType = pamet.note_state_type_by_view(ViewType.__name__)
        note_props = child.asdict()
        note_id = note_props.pop('id')
        nv_state = StateType(id=note_id, **note_props)
        fsm.add_state(nv_state)
        page_view_state.note_view_states.add(nv_state)
    elif isinstance(child, Arrow):
        arrow_props = child.asdict()
        arrow_id = arrow_props.pop('id')
        arrow_view_state = ArrowViewState(id=arrow_id, **arrow_props)
        fsm.add_state(arrow_view_state)
        page_view_state.arrow_view_states.add(arrow_view_state)

    fsm.update_state(page_view_state)


@action('map_page.handle_child_removed', issuer='entity_change_apply_logic')
def handle_child_removed(page_view_state: MapPageViewState, child: Entity):
    if isinstance(child, Note):
        nv_states = list(
            filter(lambda x: x.note_gid == child.gid(),
                   page_view_state.note_view_states))
        for nv_state in nv_states:  # Should be len==1
            fsm.remove_state(nv_state)
            page_view_state.note_view_states.remove(nv_state)
    elif isinstance(child, Arrow):
        av_states = list(
            filter(lambda x: x.arrow_gid == child.gid(),
                   page_view_state.arrow_view_states))
        for nv_state in av_states:  # Should be len==1
            fsm.remove_state(nv_state)
            page_view_state.arrow_view_states.remove(nv_state)

    fsm.update_state(page_view_state)


@action('map_page.handle_child_updated', issuer='entity_change_apply_logic')
def handle_child_updated(child_view_state: NoteViewState, child: Note):
    if isinstance(child, Note):
        child_view_state.update_from_note(child)
    elif isinstance(child, Arrow):
        child_view_state.update_from_arrow(child)
    fsm.update_state(child_view_state)


@action('map_page.handle_page_name_updated',
        issuer='entity_change_apply_logic')
def handle_page_name_updated(tab_view_state: TabViewState, page: Page):
    tab_view_state.title = page.name
    fsm.update_state(tab_view_state)


@action('map_page.start_arrow_creation')
def start_arrow_creation(map_page_view_state: MapPageViewState):
    av_state = ArrowViewState().in_page(page_id=map_page_view_state.page_id)
    fsm.add_state(av_state)

    map_page_view_state.set_mode(MapPageMode.CREATE_ARROW)
    map_page_view_state.new_arrow_view_states.append(av_state)
    fsm.update_state(map_page_view_state)


@action('map_page.abort_special_mode')
def abort_special_mode(map_page_view_state: MapPageViewState):
    # Reset the manipulated views
    # For child moving
    for note_state in map_page_view_state.moved_note_states:
        note_state.update_from_note(note_state.get_note())
        fsm.update_state(note_state)

    for arrow_state in map_page_view_state.moved_arrow_states:
        arrow_state.update_from_arrow(arrow_state.get_arrow())
        fsm.update_state(arrow_state)

    # For note resizing
    for note_state in map_page_view_state.note_resize_states:
        note_state.update_from_note(note_state.get_note())
        fsm.update_state(note_state)

    # Restore the arrow view if there was edge dragging
    if map_page_view_state.mode() == MapPageMode.ARROW_EDGE_DRAG:
        map_page_view_state.arrow_with_visible_cps.update_from_arrow(
            map_page_view_state.arrow_with_visible_cps.get_arrow())

    map_page_view_state.clear_mode()
    fsm.update_state(map_page_view_state)


@action('map_page.place_arrow_view_tail')
def place_arrow_view_tail(arrow_view_state: ArrowViewState,
                          fixed_pos: Point2D,
                          anchor_note_id: str = None,
                          anchor_type: ArrowAnchorType = ArrowAnchorType.NONE):
    arrow_view_state.set_tail(fixed_pos, anchor_note_id, anchor_type)
    fsm.update_state(arrow_view_state)


@action('map_page.place_arrow_view_head')
def place_arrow_view_head(arrow_view_state: ArrowViewState,
                          fixed_pos: Point2D,
                          anchor_note_id: str = None,
                          anchor_type: ArrowAnchorType = ArrowAnchorType.NONE):
    arrow_view_state.set_head(fixed_pos, anchor_note_id, anchor_type)
    fsm.update_state(arrow_view_state)


@action('map_page.arrow_creation_click')
def arrow_creation_click(map_page_view_state: MapPageViewState,
                         fixed_pos: Point2D = None,
                         anchor_note_id: str = None,
                         anchor_type: ArrowAnchorType = ArrowAnchorType.NONE):
    should_finish = False

    for arrow_vs in map_page_view_state.new_arrow_view_states:
        if not (arrow_vs.has_tail_anchor() or arrow_vs.tail_point):
            place_arrow_view_tail(arrow_vs, fixed_pos, anchor_note_id,
                                  anchor_type)
            if should_finish:
                raise Exception(
                    'Some of the arrows have tails while others don\'t')
        else:
            place_arrow_view_head(arrow_vs, fixed_pos, anchor_note_id,
                                  anchor_type)
            should_finish = True

    if should_finish:
        finish_arrow_creation(map_page_view_state)


@action('map_page.arrow_creation_move')
def arrow_creation_move(map_page_view_state: MapPageViewState,
                        fixed_pos: Point2D = None,
                        anchor_note_id: str = None,
                        anchor_type: ArrowAnchorType = ArrowAnchorType.NONE):
    for av_state in map_page_view_state.new_arrow_view_states:
        place_arrow_view_head(av_state, fixed_pos)


@action('map_page.finish_arrow_creation')
def finish_arrow_creation(map_page_view_state: MapPageViewState):
    for arrow_vs in map_page_view_state.new_arrow_view_states:
        # If both ends of the arrow are at the same point - cancel it
        if arrow_vs.tail_point and arrow_vs.head_point:
            if arrow_vs.tail_point == arrow_vs.head_point:
                continue

        # Similarly if both ends are on the same anchor of the same note -
        # cancel it
        if arrow_vs.has_tail_anchor() and arrow_vs.has_head_anchor():
            if (arrow_vs.tail_note_id == arrow_vs.head_note_id
                    and arrow_vs.tail_anchor == arrow_vs.head_anchor):
                continue

        # Get the properties for the new arrow from the view state
        arrow_dict = arrow_vs.asdict()
        # The new arrow should have a new id in order to avoid
        # conflicts while the mock arrow is still present
        arrow_dict.pop('id')
        arrow = Arrow.in_page(page_id=arrow_vs.page_id)
        # Since the view state has extra attributes
        arrow.replace_silent(**arrow_dict)
        pamet.insert_arrow(arrow)

    map_page_view_state.clear_mode()
    fsm.update_state(map_page_view_state)


@action('map_page.start_arrow_edge_drag')
def start_arrow_edge_drag(map_page_view_state: MapPageViewState,
                          mouse_pos: Point2D, edge_index: float):
    map_page_view_state.dragged_edge_index = edge_index
    map_page_view_state.set_mode(MapPageMode.ARROW_EDGE_DRAG)
    fsm.update_state(map_page_view_state)


@action('map_page.arrow_edge_drag_update')
def arrow_edge_drag_update(
        map_page_view_state: MapPageViewState,
        fixed_pos: Point2D = None,
        anchor_note_id: str = None,
        anchor_type: ArrowAnchorType = ArrowAnchorType.NONE):
    arrow_vs: ArrowViewState = map_page_view_state.arrow_with_visible_cps

    if map_page_view_state.dragged_edge_index == 0:
        place_arrow_view_tail(arrow_vs, fixed_pos, anchor_note_id, anchor_type)

    elif map_page_view_state.dragged_edge_index == arrow_vs.edge_indices()[-1]:
        place_arrow_view_head(arrow_vs, fixed_pos, anchor_note_id, anchor_type)

    elif map_page_view_state.dragged_edge_index in arrow_vs.edge_indices(
    ):  # Mid points
        mid_point_idx = int(map_page_view_state.dragged_edge_index - 1)
        mid_points = arrow_vs.mid_points
        mid_points[mid_point_idx] = fixed_pos
        arrow_vs.replace_midpoints(mid_points)

    else:  # .5 indices, so a potential edge, that we must create
        arrow = arrow_vs.get_arrow()
        mid_point_idx = int(map_page_view_state.dragged_edge_index // 1)
        mid_points = arrow.mid_points
        mid_points.insert(mid_point_idx, fixed_pos)
        arrow.replace_midpoints(mid_points)

        arrow_vs.update_from_arrow(arrow)  # Just to be sure
        pamet.update_arrow(arrow)

        map_page_view_state.dragged_edge_index = 1 + mid_point_idx
        fsm.update_state(map_page_view_state)
    fsm.update_state(arrow_vs)


@action('map_page.finish_arrow_edge_drag')
def finish_arrow_edge_drag(
        map_page_view_state: MapPageViewState,
        fixed_pos: Point2D = None,
        anchor_note_id: str = None,
        anchor_type: ArrowAnchorType = ArrowAnchorType.NONE):
    arrow = map_page_view_state.arrow_with_visible_cps.get_arrow()

    if map_page_view_state.dragged_edge_index == 0:
        arrow.set_tail(fixed_pos, anchor_note_id, anchor_type)

    elif map_page_view_state.dragged_edge_index == arrow.edge_indices()[-1]:
        arrow.set_head(fixed_pos, anchor_note_id, anchor_type)

    elif map_page_view_state.dragged_edge_index in arrow.edge_indices(
    ):  # Mid points
        mid_point_idx = int(map_page_view_state.dragged_edge_index - 1)
        mid_points = arrow.mid_points
        mid_points[mid_point_idx] = fixed_pos
        arrow.replace_midpoints(mid_points)

    else:  # .5 indices, so a potential edge, that we must create
        return

    pamet.update_arrow(arrow)
    map_page_view_state.clear_mode()
    fsm.update_state(map_page_view_state)


@action('map_page.delete_control_point')
def delete_arrow_edge(arrow_view_state: ArrowViewState, edge_index: float):
    if edge_index == 0 or edge_index == arrow_view_state.edge_indices()[-1]:
        raise Exception('Cannot remove the tail or head')
    if edge_index not in arrow_view_state.edge_indices():
        raise Exception(f'Cannot remove edge with index {edge_index}')

    arrow = arrow_view_state.get_arrow()
    mid_points = arrow.mid_points
    mid_points.pop(edge_index - 1)
    arrow.replace_midpoints(mid_points)
    pamet.update_arrow(arrow)


@action('map_page.autosize_selected_notes')
def autosize_selected_notes(map_page_view_state: MapPageViewState):
    # views.note.qt_helpers.elide_text should be fixed to not use any Qt stuff
    # in order for this to work on web. The latter only requires abstracting
    # QFontMetrics.boundingRect (that works for single lines) and elideText
    # for single words
    for note_vs in map_page_view_state.selected_children:
        if not isinstance(note_vs, (TextNote, CardNote, ImageNote)):
            continue

        note = note_vs.get_note()
        old_size = note.rect().size()
        new_size = minimal_nonelided_size(note)
        if new_size == old_size:
            continue

        rect = note.rect()
        rect.set_size(snap_to_grid(new_size))
        note.set_rect(rect)
        pamet.update_note(note)


@action('map_page.undo')
def undo(map_page_view_state: MapPageViewState):
    page = pamet.page(map_page_view_state.page_id)
    pamet.undo_service().back_one_step(page.id)


@action('map_page.redo')
def redo(map_page_view_state: MapPageViewState):
    page = pamet.page(map_page_view_state)
    pamet.undo_service().forward_one_step(page.id)


@action('map_page.copy_selected_children')
def copy_selected_children(map_page_view_state: MapPageViewState,
                           relative_to: Point2D = None):
    copied_notes = []
    positions = []
    for child_vs in map_page_view_state.selected_children:
        # If note view - get note and translate position
        if not isinstance(child_vs, NoteViewState):
            continue

        note: Note = child_vs.get_note()
        positions.append(note.rect().top_left())
        copied_notes.append(note)

    if not copied_notes:
        return

    # If there is no reference point - get the middle of the group
    if not relative_to:
        relative_to = sum(positions) / len(positions)

    # Move the notes relative to the reference point before adding them to the
    # clipboard (since pasting happens relative to the mouse)
    for note in copied_notes:
        rect: Rectangle = note.rect()

        # If there's just one note selected - we don't want a relative pos
        if len(copied_notes) == 1:
            rect.set_top_left(Point2D(0, 0))
        else:
            rect.set_top_left(rect.top_left() - relative_to)
        note.set_rect(rect)

    # If arrow view - get arrow and if not both notes are copied - skip
    # else translate and add to the list
    copied_arrows = []
    for child_vs in map_page_view_state.selected_children:
        # If note view - get note and translate position
        if not isinstance(child_vs, ArrowViewState):
            continue

        arrow: Arrow = child_vs.get_arrow()

        # Check for tail and head notes - if not present - don't copy the arrow
        if arrow.has_head_anchor():
            if arrow.head_note_id not in (note.id for note in copied_notes):
                continue
        else:  # If it's a fixed pos - translate it relative to relative_to
            arrow.set_head(fixed_pos=arrow.head_point - relative_to)

        if arrow.has_tail_anchor():
            if arrow.tail_note_id not in (note.id for note in copied_notes):
                continue
        else:
            arrow.set_tail(fixed_pos=arrow.tail_point - relative_to)

        mid_points = arrow.mid_points
        mid_points = [mid_point - relative_to for mid_point in mid_points]
        arrow.replace_midpoints(mid_points)

        copied_arrows.append(arrow)
    pamet.clipboard.set_contents(copied_notes + copied_arrows)


@action('map_page.paste')
def paste(map_page_view_state: MapPageViewState, relative_to: Point2D = None):
    page = pamet.page(map_page_view_state.id)
    entities = pamet.clipboard.get_contents()

    updated_ids = {}
    for note in entities:
        if not isinstance(note, Note):
            continue
        if relative_to:
            rect: Rectangle = note.rect()
            top_left = snap_to_grid(relative_to + rect.top_left())
            rect.set_top_left(top_left)
            note.set_rect(rect)

        # Set the proper page id and ensure that there's no conflicting ids
        new_page_id = page.id
        new_own_id = note.own_id
        if pamet.find(gid=note.gid()):
            new_own_id = get_entity_id()
            updated_ids[note.id] = new_own_id
        note = note.with_id(page_id=new_page_id, own_id=new_own_id)
        pamet.insert_note(note)

    for arrow in entities:
        if not isinstance(arrow, Arrow):
            continue

        # Set the proper page id and ensure that there's no conflicting ids
        new_page_id = page.id
        new_own_id = arrow.own_id
        if pamet.find(gid=arrow.gid()):
            new_own_id = get_entity_id()
        arrow = arrow.with_id(page_id=new_page_id, own_id=new_own_id)

        # Where the pasted note ids have been changed - correct them
        # in the arrow anchors. Else for fixed anchors - just place them
        # relative to the mouse
        if arrow.has_tail_anchor():
            if arrow.tail_note_id in updated_ids:
                arrow.tail_note_id = updated_ids[arrow.tail_note_id]
        else:
            if relative_to:
                arrow.tail_point = snap_to_grid(relative_to + arrow.tail_point)

        if arrow.has_head_anchor():
            if arrow.head_note_id in updated_ids:
                arrow.head_note_id = updated_ids[arrow.head_note_id]
        else:
            if relative_to:
                arrow.head_point = snap_to_grid(relative_to + arrow.head_point)

        if relative_to:
            mid_points = arrow.mid_points
            mid_points = [
                snap_to_grid(relative_to + mid_point)
                for mid_point in mid_points
            ]
            arrow.replace_midpoints(mid_points)

        pamet.insert_arrow(arrow)


@action('map_page.cut_selected_children')
def cut_selected_children(map_page_view_state: MapPageViewState,
                          relative_to: Point2D = None):
    copy_selected_children(map_page_view_state, relative_to)
    delete_selected_children(map_page_view_state)


@action('map_page.paste_special')
def paste_special(map_page_view_state: MapPageViewState,
                  relative_to: Point2D = None):
    entities = pamet.clipboard.convert_external()

    next_spawn_pos = relative_to or map_page_view_state.center()
    for note in entities:
        note = note.with_id(page_id=map_page_view_state.page_id)
        rect = note.rect()

        # Autosize
        if isinstance(note, (TextNote, CardNote, ImageNote)):
            new_size = minimal_nonelided_size(note)
            rect.set_size(snap_to_grid(new_size))

        # Move under the last one
        rect.set_top_left(next_spawn_pos)

        # Update the spawn pos to be one unit under the last note
        next_spawn_pos = rect.bottom_left()
        next_spawn_pos += Point2D(0, ALIGNMENT_GRID_UNIT)

        # Insert the note
        note.set_rect(rect)
        pamet.insert_note(note)
