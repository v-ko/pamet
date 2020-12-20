import misli
from misli.core.primitives import Point
from misli.gui.actions_lib import action

log = misli.get_logger(__name__)


@action('map_page.start_mouse_drag_navigation')
def start_mouse_drag_navigation(
        map_page_component_id: int, position):
    map_page_component = misli.gui.component(map_page_component_id)

    map_page_component.mouse_drag_navigation_active = True
    map_page_component.mouse_position_on_left_press = Point(*position)

    misli.gui.update_component(map_page_component_id)


@action('map_page.change_viewport_center')
def change_viewport_center(map_page_component_id: int, new_viewport_center):
    map_page_component = misli.gui.component(map_page_component_id)

    map_page_component.viewport.set_center(Point(*new_viewport_center))
    misli.gui.update_component(map_page_component_id)


@action('map_page.stop_mouse_drag_navigation')
def stop_mouse_drag_navigation(
        map_page_component_id: int, new_viewport_center):
    map_page_component = misli.gui.component(map_page_component_id)

    map_page_component.viewport.set_center(new_viewport_center)
    misli.gui.update_component(map_page_component_id)


@action('map_page.update_note_selections')
def update_note_selections(map_page_component_id: int,
                           selection_updates_by_note_id: dict):

    map_page_component = misli.gui.component(map_page_component_id)

    if not selection_updates_by_note_id:
        return

    selection_update_count = 0

    for note_id, selected in selection_updates_by_note_id.items():
        if note_id in map_page_component.selected_nc_ids and not selected:
            map_page_component.selected_nc_ids.remove(note_id)
            selection_update_count += 1

        elif note_id not in map_page_component.selected_nc_ids and selected:
            map_page_component.selected_nc_ids.add(note_id)
            selection_update_count += 1

        else:
            log.warning('Redundant entry in selection_updates_by_note_id')

    if selection_update_count > 0:
        misli.gui.update_component(map_page_component.id)
        # log.info('Updated %s selections' % selection_update_count)
    else:
        log.info('No selections updated out of %s' %
                 selection_updates_by_note_id)

    misli.gui.update_component(map_page_component_id)


@action('map_page.clear_note_selection')
def clear_note_selection(map_page_component_id: int):
    map_page_component = misli.gui.component(map_page_component_id)

    selection_updates = {}
    for sc_id in map_page_component.selected_nc_ids:
        selection_updates[sc_id] = False

    if not selection_updates:
        return

    update_note_selections(map_page_component_id, selection_updates)


@action('map_page.set_viewport_height')
def set_viewport_height(map_page_component_id: int, new_height: float):
    map_page_component = misli.gui.component(map_page_component_id)
    map_page_component.viewport.eyeHeight = new_height

    for child in map_page_component.get_children():
        # child.image_cache = None
        child.should_reallocate_image_cache = True
        child.shoud_rerender_image_cache = True

    misli.gui.update_component(map_page_component_id)
    # //glutPostRedisplay(); artefact, thank you for siteseeing


@action('map_page.start_drag_select')
def start_drag_select(map_page_component_id, position):
    map_page_component = misli.gui.component(map_page_component_id)

    map_page_component.mouse_position_on_left_press = Point(*position)
    map_page_component.drag_select_active = True
    misli.gui.update_component(map_page_component_id)


@action('map_page.update_drag_select')
def update_drag_select(
        map_page_component_id, rect_props: list, drag_selected_nc_ids=None):

    map_page_component = misli.gui.component(map_page_component_id)

    if drag_selected_nc_ids is None:
        drag_selected_nc_ids = []

    map_page_component.drag_select_rect_props = rect_props
    map_page_component.drag_select_nc_ids.clear()

    for nc_id in drag_selected_nc_ids:
        if nc_id not in map_page_component.drag_select_nc_ids:
            map_page_component.drag_select_nc_ids.append(nc_id)

    misli.gui.update_component(map_page_component_id)


@action('map_page.stop_drag_select')
def stop_drag_select(map_page_component_id):
    map_page_component = misli.gui.component(map_page_component_id)

    map_page_component.drag_select_active = False
    map_page_component.selected_nc_ids.update(
        map_page_component.drag_select_nc_ids)
    map_page_component.drag_select_nc_ids.clear()

    misli.gui.update_component(map_page_component_id)


@action('map_page.delete_selected_notes')
def delete_selected_notes(map_page_component_id):
    map_page_component = misli.gui.component(map_page_component_id)

    for nc_id in map_page_component.selected_nc_ids:
        note = misli.gui.base_object_for_component(nc_id)
        misli.delete_note(note.id, note.page_id)


@action('map_page.start_notes_resize')
def start_notes_resize(map_page_component_id):
    map_page_component = misli.gui.component(map_page_component_id)

    map_page_component.note_resize_active = True
    misli.gui.update_component(map_page_component_id)


@action('map_page.resize_note_components')
def resize_note_components(map_page_component_id, new_size, nc_ids):
    for nc_id in nc_ids:
        nc = misli.gui.component(nc_id)
        note = nc.note()

        note.set_size(Point(*new_size))  # Here size restrictions are applied
        nc.set_props_from_base_object(**note.state())
        nc.should_rebuild_pcommand_cache = True
        nc.should_reallocate_image_cache = True
        nc.shoud_rerender_image_cache = True

        misli.gui.update_component(nc.id)
    misli.gui.update_component(map_page_component_id)


@action('map_page.resize_notes')
def resize_notes(new_size, page_id, note_ids):
    page = misli.page(page_id)
    for note_id in note_ids:
        note = page.note(note_id)

        note.set_size(new_size)
        misli.update_note(**note.state())


@action('map_page.stop_notes_resize')
def stop_notes_resize(map_page_component_id, new_size, nc_ids):
    map_page_component = misli.gui.component(map_page_component_id)

    map_page_component.note_resize_active = False

    page = misli.gui.base_object_for_component(map_page_component_id)
    note_ids = [misli.gui.base_object_for_component(nc_id).id
                for nc_id in nc_ids]
    resize_notes(new_size, page.id, note_ids)

    misli.gui.update_component(map_page_component_id)
