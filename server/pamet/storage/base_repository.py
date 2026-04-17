from typing import Generator

from fusion.storage.base_store import Store
from fusion.storage.change import Change
from fusion.util import current_time

from pamet.model.arrow import Arrow
from pamet.model.note import Note
from pamet.model.page import Page


class PametStore(Store):
    """Pamet-specific domain store matching TS PametStore.

    Provides typed CRUD convenience methods on top of the generic Store.
    Store methods are pure data operations that return Changes.
    Side effects (view updates, commit/save) belong in the concrete
    runtime wrapper (like TS FrontendDomainStore).
    """

    def __init__(self) -> None:
        self.home_page_id = None

    # -------------Pages CRUD-------------
    def insert_page(self, page_: Page) -> Change:
        return self.insert_one(page_)

    def update_page(self, page_: Page) -> Change:
        old_page = self.find_one(id=page_.id)
        if not old_page:
            raise Exception("Can not update missing page.")

        if page_.path != old_page.path:
            page_.datetime_modified = current_time()

        return self.update_one(page_)

    def remove_page(self, page_: Page) -> Change:
        return self.remove_one(page_)

    def pages(self, **filter) -> Generator[Page, None, None]:
        filter["type"] = Page
        return self.find(**filter)

    def page(self, page_id: str) -> Page | None:
        if not page_id:
            return None
        return self.find_one(id=page_id)

    # -------------Notes CRUD-------------
    def insert_note(self, note_: Note) -> Change:
        return self.insert_one(note_)

    def update_note(self, note_: Note) -> Change:
        old_note = self.find_one(id=note_.id)
        if not old_note:
            raise Exception("Can not update missing note.")

        if note_.content != old_note.content:
            note_.datetime_modified = current_time()

        return self.update_one(note_)

    def remove_note(self, note_: Note) -> Change:
        return self.remove_one(note_)

    def notes(self, page_id: str) -> Generator[Note, None, None]:
        return self.find(parent_id=page_id, type=Note)

    def note(self, note_id: str) -> Note | None:
        return self.find_one(id=note_id, type=Note)

    # -------------Arrow CRUD-------------
    def insert_arrow(self, arrow_: Arrow) -> Change:
        return self.insert_one(arrow_)

    def update_arrow(self, arrow_: Arrow) -> Change:
        old_arrow = self.find_one(id=arrow_.id)
        if not old_arrow:
            raise Exception("Can not update missing arrow")

        return self.update_one(arrow_)

    def remove_arrow(self, arrow_: Arrow) -> Change:
        return self.remove_one(arrow_)

    def arrows(self, page_id: str) -> Generator[Arrow, None, None]:
        return self.find(parent_id=page_id, type=Arrow)

    def arrow(self, arrow_id: str) -> Arrow | None:
        return self.find_one(id=arrow_id, type=Arrow)

    # Other
    def home_page(self) -> Page | None:
        if not self.home_page_id:
            return None
        return self.page(self.home_page_id)

    def set_home_page(self, new_page: Page):
        self.home_page_id = new_page.id
