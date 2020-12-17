import misli
from misli.objects.change import ChangeTypes
from misli.objects import BaseObject

from misli import get_logger
log = get_logger(__name__)


class Repository(BaseObject):
    def __init__(self):
        BaseObject.__init__(self, obj_type='Repository')

        self._pages = {}

    def create_page(self, **page_state):
        raise NotImplementedError

    def page_ids(self):
        raise NotImplementedError

    def page_state(self, page_id):
        raise NotImplementedError

    def update_page(self, page_state):
        raise NotImplementedError

    def delete_page(self, page_id):
        raise NotImplementedError

    def save_changes(self, changes):
        pages_for_update = {}

        savable_changes = [ChangeTypes.CREATE,
                           ChangeTypes.DELETE,
                           ChangeTypes.UPDATE]

        for change in changes:
            last_state = change.last_state()

            if last_state['obj_type'] == 'Note':
                if change.type in savable_changes:
                    page = misli.page(last_state['page_id'])
                    pages_for_update[page.id] = page.state()

            elif last_state['obj_type'] == 'Page':
                if change.type == ChangeTypes.CREATE:
                    self.create_page(**last_state)

                elif change.type == ChangeTypes.UPDATE:
                    pages_for_update[last_state['id']] = last_state

                elif change.type == ChangeTypes.DELETE:
                    self.delete_page(last_state['id'])

        for page_id, page_state in pages_for_update.items():
            self.update_page(**page_state)
