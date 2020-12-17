import misli
from misli.gui.actions_lib import action

log = misli.get_logger(__name__)


@action('map_page.mouse_drag_navigation')
def mouse_drag_navigation(map_page_component_id: int, new_viewport_center):
    map_page_component = misli.gui.component(map_page_component_id)

    map_page_component.viewport.set_center(new_viewport_center)
    misli.gui.update_component(map_page_component_id)


@action('map_page.update_note_selections')
def update_note_selections(map_page_component_id: int,
                           selection_updates: dict):

    map_page_component = misli.gui.component(map_page_component_id)

    if not selection_updates:
        return

    selection_update_count = 0

    for note_id, selected in selection_updates.items():
        if note_id in map_page_component.selected_nc_ids and not selected:
            map_page_component.selected_nc_ids.remove(note_id)
            selection_update_count += 1

        elif note_id not in map_page_component.selected_nc_ids and selected:
            map_page_component.selected_nc_ids.add(note_id)
            selection_update_count += 1

        else:
            log.warning('Redundant entry in selection_updates')

    if selection_update_count > 0:
        misli.gui.update_component(map_page_component.id)
        # log.info('Updated %s selections' % selection_update_count)
    else:
        log.info('No selections updated out of %s' % selection_updates)

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
        child.cache['render_cache_expired'] = True

    misli.gui.update_component(map_page_component_id)
    # //glutPostRedisplay(); artefact, thank you for siteseeing


@action('map_page.update_drag_select')
def update_drag_select(
        map_page_component_id: int, select_rect=None, drag_selected_nc_ids=[]):

    map_page_component = misli.gui.component(map_page_component_id)

    if not select_rect:
        map_page_component.drag_select.active = False
        map_page_component.selected_nc_ids.update(
            map_page_component.drag_select.nc_ids)

        map_page_component.drag_select.nc_ids.clear()
    else:
        map_page_component.drag_select.active = True
        map_page_component.drag_select.nc_ids.clear()

        for nc_id in drag_selected_nc_ids:
            if nc_id not in map_page_component.selected_nc_ids:
                map_page_component.drag_select.nc_ids.append(nc_id)

    misli.gui.update_component(map_page_component_id)


@action('map_page.delete_selected_notes')
def delete_selected_notes(map_page_component_id):
    map_page_component = misli.gui.component(map_page_component_id)

    for nc_id in map_page_component.selected_nc_ids:
        note = misli.gui.base_object_for_component(nc_id)
        misli.delete_note(note.id, note.page_id)
