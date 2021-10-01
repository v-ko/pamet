from typing import List

import misli
from misli.gui import action
from misli import Entity, Change, ChangeTypes

import pamet
from pamet.gui import entity_to_view_mapping, create_and_bind_note_view

log = misli.get_logger(__name__)


@action('update_views_for_page_changes')
def update_views_for_page_changes(changes: List[dict]):
    for page_change_dict in changes:
        page_change = Change(**page_change_dict)
        page_state = page_change.last_state()
        _page = Entity.from_dict(page_state)

        if page_change.is_update():

            page_views = entity_to_view_mapping.views_for(_page.gid())
            for pc in page_views:
                pcs = misli.gui.view_state(pc.id)
                pcs.page = _page
                misli.gui.update_state(pc.id)

        elif page_change.is_delete():
            page_views = entity_to_view_mapping.views_for(_page.gid())
            for pc in page_views:
                misli.gui.remove_view(pc)
                # I may have to do something more elegant here - with
                # some kind of notification

        elif page_change.is_create():
            pass


@action('update_views_for_note_changes')
def update_views_for_note_changes(changes: List[dict]):
    for note_change_dict in changes:
        note_change = Change(**note_change_dict)
        _note = Entity.from_dict(note_change.last_state())

        if note_change.is_create():
            _page = pamet.page(_note.page_id)
            page_views = entity_to_view_mapping.views_for(_page.gid())

            # Create a note component for all opened views for its page
            for pc in page_views:
                create_and_bind_note_view(pc.id, _note)

        elif note_change.is_update():
            note_views = entity_to_view_mapping.views_for(_note.gid())

            for nc in note_views:
                ncs = misli.gui.view_state(nc.id)
                ncs.note = _note
                misli.gui.update_state(ncs)

        elif note_change.type == ChangeTypes.DELETE:
            note_views = entity_to_view_mapping.views_for(_note.gid())
            for nc in note_views:
                misli.gui.remove_view(nc)
