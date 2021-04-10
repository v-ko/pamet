import pamet
from misli.change import ChangeTypes, Change
from pamet.entities import Page

from misli import get_logger
log = get_logger(__name__)


class Repository:
    def __init__(self):
        self.path = ''
        self._pages = {}

    def create_page(self, page, notes):
        raise NotImplementedError

    def page_ids(self):
        raise NotImplementedError

    def page_with_notes(self, page_id):
        raise NotImplementedError

    def update_page(self, page_state):
        raise NotImplementedError

    def delete_page(self, page_id):
        raise NotImplementedError

    def save_changes(self, changes):
        pages_for_update = {}  # {id: True}

        savable_changes = [ChangeTypes.CREATE,
                           ChangeTypes.DELETE,
                           ChangeTypes.UPDATE]

        for change_dict in changes:
            change = Change(**change_dict)
            last_state = change.last_state()

            if last_state['obj_type'] == 'Note':
                if change.type in savable_changes:
                    pages_for_update[last_state['page_id']] = True

            elif last_state['obj_type'] == 'MapPage':
                if change.type == ChangeTypes.CREATE:
                    self.create_page(Page.from_dict(last_state), [])

                elif change.type == ChangeTypes.UPDATE:
                    pages_for_update[last_state['id']] = True

                elif change.type == ChangeTypes.DELETE:
                    self.delete_page(last_state['id'])

            else:
                raise NotImplementedError

        for page_id, _ in pages_for_update.items():
            page = pamet.page(page_id)
            notes = pamet.notes(page.id)
            self.update_page(page, notes)
