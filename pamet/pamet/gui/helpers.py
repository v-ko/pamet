import misli
import pamet
from pamet.gui import entity_to_view_mapping

log = misli.get_logger(__name__)


@log.traced
def create_and_bind_page_view(page_id: str, parent_id: str):
    _page = pamet.page(page_id)

    page_view_class = misli.gui.view_library.get_view_class(
        obj_type=_page.obj_type)
    page_view = page_view_class(parent_id=parent_id)

    page_view_state = page_view.state
    page_view_state.page = _page
    misli.gui.update_state(page_view_state)

    entity_to_view_mapping.map(_page.gid(), page_view.id)

    for _note in pamet.notes(_page.id):
        create_and_bind_note_view(page_view.id, _note)

    return page_view


@log.traced
def create_and_bind_note_view(page_view_id, _note):
    note_view_class = misli.gui.view_library.get_view_class(
        obj_type=_note.obj_type, edit=False)
    note_view = note_view_class(parent_id=page_view_id)

    note_view_state = note_view.state
    note_view_state.note = _note
    misli.gui.update_state(note_view_state)

    entity_to_view_mapping.map(_note.gid(), note_view.id)
    return note_view


@log.traced
def create_and_bind_edit_view(tab_view_id, _note):
    edit_class = misli.gui.view_library.get_view_class(obj_type=_note.obj_type,
                                                       edit=True)
    edit_view = edit_class(parent_id=tab_view_id)

    edit_view_state = edit_view.state
    edit_view_state.note = _note
    misli.gui.update_state(edit_view_state)

    entity_to_view_mapping.map(_note.gid(), edit_view.id)

    return edit_view
