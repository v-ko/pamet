from misli.entities import Page
from .repository import Repository

from misli import get_logger
log = get_logger(__name__)


class InMemoryRepository(Repository):
    def __init__(self):
        Repository.__init__(self)

        self._pages = {}
        self.path = 'in-memory'

    def create_page(self, **page_state):
        page = Page(**page_state)
        self._pages[page.id] = page

    def page_ids(self):
        return list(self._pages.keys())

    def page_state(self, page_id):
        if page_id not in self._pages:
            return None

        return self._pages[page_id].state()

    def update_page(self, page_state):
        page = Page(**page_state)
        self._pages[page.id] = page

    def delete_page(self, page_id):
        if page_id in self._pages:
            del self._pages[page_id]

        else:
            log.error('Cannot delete missing page %s' % page_id)
