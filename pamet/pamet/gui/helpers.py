import misli
import pamet

log = misli.get_logger(__name__)


@log.traced
def create_and_bind_page_view(page_id: str, parent_id: str):
    _page = pamet.page(page_id)
    page_view = misli.gui.create_view(
        parent_id,
        view_class_metadata_filter=dict(obj_type=_page.obj_type),
        mapped_entity=_page)

    for _note in pamet.notes(_page.id):
        create_and_bind_note_view(page_view.id, _note)

    return page_view


@log.traced
def create_and_bind_note_view(page_view_id, _note):
    note_view = misli.gui.create_view(
        parent_id=page_view_id,
        view_class_metadata_filter=dict(obj_type=_note.obj_type),
        mapped_entity=_note)

    return note_view


@log.traced
def create_and_bind_edit_view(tab_view_id, _note):
    edit_view = misli.gui.create_view(
        parent_id=tab_view_id,
        view_class_metadata_filter=dict(obj_type=_note.obj_type, edit=True),
        mapped_entity=_note)

    return edit_view
