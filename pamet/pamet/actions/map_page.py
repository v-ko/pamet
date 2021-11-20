import misli
from misli import gui
import pamet

from misli.basic_classes import Point2D
from misli.gui.actions_library import action
from pamet.model import Note, Page
from pamet.actions import tab as tab_actions
from pamet.views.map_page.view import MapPageViewState
from pamet.views.tab.view import TabViewState

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
                         map_page_view_state.viewport.height_scale_factor())
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
def update_note_selections(map_page_view_id: str,
                           selection_updates_by_note_id: dict):

    map_page_view_state = gui.view_state(map_page_view_id)

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
def clear_note_selection(map_page_view_id: str):
    map_page_view_state = gui.view_state(map_page_view_id)

    selection_updates = {}
    for sc_id in map_page_view_state.selected_nc_ids:
        selection_updates[sc_id] = False

    if not selection_updates:
        return

    update_note_selections(map_page_view_id, selection_updates)


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
def delete_selected_notes(map_page_view_id: str):
    map_page_view_state = gui.view_state(map_page_view_id)

    for nc_id in map_page_view_state.selected_nc_ids:
        ncs = gui.view_state(nc_id)
        misli.remove(ncs.note)


@action('map_page.start_notes_resize')
def start_notes_resize(map_page_view_id: str, main_note: Note,
                       mouse_position: Point2D,
                       resize_circle_center_projected: Point2D):

    map_page_view_state = gui.view_state(map_page_view_id)

    map_page_view_state.note_resize_delta_from_note_edge = (
        resize_circle_center_projected - mouse_position)
    map_page_view_state.note_resize_click_position = mouse_position
    map_page_view_state.note_resize_main_note = main_note

    map_page_view_state.note_resize_active = True
    gui.update_state(map_page_view_state)


@action('map_page.resize_note_views')
def resize_note_views(map_page_view_id: str, new_size: list, nc_ids: list):

    for nc_id in nc_ids:
        ncs = gui.view_state(nc_id)
        note = ncs.note

        note.set_size(Point2D(*new_size))  # Here size restrictions are applied
        gui.update_state(ncs)


@action('map_page.resize_notes')
def resize_notes(new_size: list, page_id: str, note_ids: list):
    page = pamet.page(gid=page_id)
    for note_id in note_ids:
        note = page.note(note_id)

        note.set_size(new_size)
        misli.update(note)


@action('map_page.stop_notes_resize')
def stop_notes_resize(map_page_view_id: str, new_size: list, nc_ids: list):

    map_page_view_state = gui.view_state(map_page_view_id)
    map_page_view_state.note_resize_active = False

    page = map_page_view_state.page
    note_ids = [gui.view(nc_id).note.id for nc_id in nc_ids]
    resize_notes(new_size, page.id, note_ids)

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
def note_drag_nc_position_update(map_page_view_id: str, nc_ids: list,
                                 delta: list):

    d = Point2D(*delta)

    for nc_id in nc_ids:
        ncs = gui.view_state(nc_id)
        note = misli.find_one(gid=ncs.note.gid())

        ncs.note.x = note.x + d.x()
        ncs.note.y = note.y + d.y()

        gui.update_state(ncs)


@action('map_page.stop_note_drag')
def stop_note_drag(map_page_view_id: str, nc_ids: list, delta: list):
    map_page_view_state = gui.view_state(map_page_view_id)

    d = Point2D(*delta)
    for nc_id in nc_ids:
        ncs = gui.view_state(nc_id)
        note = misli.find_one(gid=ncs.note.gid())

        note.x += d.x()
        note.y += d.y()

        misli.update(note)

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
def color_selected_notes(map_page_view_id: str,
                         color: list = None,
                         background_color: list = None):
    map_page_view_state = gui.view_state(map_page_view_id)

    for nc_id in map_page_view_state.selected_nc_ids:
        note = gui.view(nc_id).note

        color = color or note.color
        background_color = background_color or note.background_color

        note.color = color
        note.background_color = background_color
        misli.update(note)

    map_page_view_state.selected_nc_ids.clear()
    misli.gui.update_state(map_page_view_state)


@action('map_page.open_context_menu')
def open_context_menu(tab_view_id: str, entries: dict):
    misli.gui.create_view(tab_view_id,
                          view_class_metadata_filter=dict(name='ContextMenu'),
                          init_kwargs=dict(entries=entries))


@action('map_page.open_page_properties')
def open_page_properties(tab_view_id: str, focused_prop: str = None):
    tab_state: TabViewState = misli.gui.view_state(tab_view_id)
    page_view_state: MapPageViewState = misli.gui.view_state(
        tab_state.page_view_id)
    properties_view = misli.gui.create_view(parent_id=tab_state.id,
                                            view_class_metadata_filter=dict(
                                                entity_type=Page.__name__,
                                                page_edit=True),
                                            mapped_entity=page_view_state.page)

    if focused_prop:
        properties_view_state = misli.gui.view_state(properties_view)
        properties_view_state.focused_prop = focused_prop
        misli.gui.update_state(properties_view_state)

    tab_state.right_sidebar_view_id = properties_view.id
    tab_state.right_sidebar_visible = True
    tab_state.page_properties_open = True

    misli.gui.update_state(tab_state)


@action('map_page.save_page_properties')
def save_page_properties(page: Page):
    misli.update(page)


@action('map_page.close_page_properties')
def close_page_properties(properties_view_id: str):
    properties_view = misli.gui.view(properties_view_id)
    tab = properties_view.get_parent()
    tab_state = tab.state()
    tab_state.right_sidebar_visible = False
    tab_state.right_sidebar_view_id = None
    tab_state.page_properties_open = False

    misli.gui.remove_view(properties_view)
    misli.gui.update_state(tab_state)


@action('map_page.delete_page')
def delete_page(tab_view_id, page):
    misli.remove(page)
    next_page = pamet.helpers.get_default_page()
    if not next_page:
        misli.gui.create_view(
            parent_id=tab_view_id,
            view_class_metadata_filter=dict(name='MessageBox'),
            init_kwargs=dict(title='Info',
                             text=('You deleted the last page. '
                                   'A blank one has been created for you')))
        next_page = pamet.actions.other.create_default_page()
    tab_actions.tab_go_to_page(tab_view_id, next_page.id)


