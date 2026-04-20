from fusion.storage.in_memory_store import InMemoryStore

from pamet.model.arrow import Arrow
from pamet.model.note import Note
from pamet.model.page import Page
from pamet.storage.base_repository import PametStore


class PametInMemoryStore(InMemoryStore, PametStore):
    def __init__(self):
        InMemoryStore.__init__(self, (Page, Note, Arrow))
