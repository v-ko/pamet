from typing import List

from misli import Entity
from misli.change import ChangeTypes, Change
from misli import get_logger

import pamet

log = get_logger(__name__)


class Repository:
    def __init__(self):
        self.path = ''
        self._pages = {}

    def page_ids(self):
        raise NotImplementedError

    def create_page(self, page, notes):
        raise NotImplementedError

    def get_page_and_notes(self, page_id):
        raise NotImplementedError

    def update_page(self, page, notes):
        raise NotImplementedError

    def delete_page(self, page_id):
        raise NotImplementedError

    def save_changes(self, changes: List[Change]):
        """Applies the received changes to the objects in the repository.

        Changes are applied in order and grouped only if consiquent changes
        refer to the same page.

        Args:
            changes (List[Change]): The list of changes to be applied

        Raises:
            NotImplementedError: If the save behavior for some object in the
            changes is undefined
        """
        page_id_for_aggregate_update = None

        def flush_aggregate_update():
            if not page_id_for_aggregate_update:
                return
            page = pamet.page(page_id_for_aggregate_update)
            notes = pamet.notes(page.id)
            self.update_page(page, notes)

        while changes:
            change_dict = changes.pop(0)
            change = Change(**change_dict)
            entity = Entity.from_dict(change.last_state())

            if entity.obj_type in ['MapPage']:  # Pages
                if change.type == ChangeTypes.CREATE:
                    flush_aggregate_update()
                    self.create_page(entity, [])

                elif change.type == ChangeTypes.UPDATE:
                    if entity.id != page_id_for_aggregate_update:
                        flush_aggregate_update()
                        page_id_for_aggregate_update = entity.id

                elif change.type == ChangeTypes.DELETE:
                    flush_aggregate_update()
                    self.delete_page(entity.id)

            elif hasattr(entity, 'page_id'):  # If it's a page child, e.g. note
                if entity.page_id != page_id_for_aggregate_update:
                    flush_aggregate_update()
                    page_id_for_aggregate_update = entity.page_id

            else:
                log.error('Saving changes for objects of type "%s" is not'
                          'implemented. Change: %s' %
                          (entity.obj_type, change_dict))
                raise NotImplementedError

        flush_aggregate_update()
