from fusion.storage.in_memory_repository import InMemoryRepository
from pamet.model.arrow import Arrow
from pamet.model.note import Note
from pamet.model.page import Page
from pamet.storage.base_repository import PametRepository


class PametInMemoryRepository(InMemoryRepository, PametRepository):
    def __init__(self):
        InMemoryRepository.__init__(self, (Page, Note, Arrow))