from typing import Generator, Union
from fusion.libs.entity.change import Change
from fusion.util import current_time
from fusion.libs.channel import Channel
from fusion.storage.repository import Repository

from pamet.model.arrow import Arrow
from pamet.model.note import Note
from pamet.model.page import Page
from pamet.model.page_child import PageChild


class PametRepository(Repository):

    def __init__(self) -> None:
        self.raw_entity_changes_channel = None
        self.default_page_id = None

    def set_change_channel(self, change_channel: Channel):
        self.raw_entity_changes_channel = change_channel

    # -------------Pages CRUD-------------
    def insert_page(self, page_: Page) -> Change:
        change = self.insert_one(page_)
        if self.raw_entity_changes_channel:
            self.raw_entity_changes_channel.push(change)
        return change

    def remove_page(self, page_: Page) -> Change:
        change = self.remove_one(page_)
        if self.raw_entity_changes_channel:
            self.raw_entity_changes_channel.push(change)
        return change

    def update_page(self, page_: Page) -> Change:
        old_page = self.find_one(id=page_.id)
        if not old_page:
            raise Exception('Can not update missing page.')

        if page_.name != old_page.name:
            page_.datetime_modified = current_time()

        change = self.update_one(page_)
        if self.raw_entity_changes_channel:
            self.raw_entity_changes_channel.push(change)
        return change

    def pages(self, **filter) -> Generator[Page, None, None]:
        filter['type'] = Page
        return self.find(**filter)

    def page(self, page_gid: str | tuple) -> Union[Page, None]:
        if not page_gid:
            return None
        return self.find_one(gid=page_gid)

    def insert_child(self, child: PageChild, page: Page = None) -> Change:
        if page and page.id != child.page_id:
            child = child.with_id(page.id, child.own_id)
        change = self.insert_one(child)
        if self.raw_entity_changes_channel:
            self.raw_entity_changes_channel.push(change)
        return change

    # -------------Notes CRUD-------------
    def insert_note(self, note: Note, page: Page = None) -> Change:
        return self.insert_child(note, page)

    def update_note(self, note_: Note) -> Change:
        old_note = self.find_one(gid=note_.gid())
        if not old_note:
            raise Exception('Can not update missing note.')

        if note_.content != old_note.content:
            note_.datetime_modified = current_time()

        change = self.update_one(note_)
        if self.raw_entity_changes_channel:
            self.raw_entity_changes_channel.push(change)
        return change

    def remove_note(self, note_: Note) -> Change:
        change = self.remove_one(note_)
        if self.raw_entity_changes_channel:
            self.raw_entity_changes_channel.push(change)
        return change

    def notes(self, page_: Page | str) -> Generator[Note, None, None]:
        page_gid = page_.gid() if isinstance(page_, Page) else page_
        return self.find(parent_gid=page_gid, type=Note)

    def note(self, page_: Page | str, note_own_id: str):
        page_gid = page_.gid() if isinstance(page_, Page) else page_
        return self.find_one(gid=(page_gid, note_own_id))

    # def notes(self, **kwargs) -> Generator[Note, None, None]:
    #     if 'type' in kwargs:
    #         raise Exception
    #     return self.find(type=Note, **kwargs)

    # def note(self, **kwargs):
    #     if 'type' in kwargs:
    #         raise Exception
    #     return self.find_one(type=Note, **kwargs)

    # -------------Arrow CRUD-------------
    def insert_arrow(self, arrow_: Arrow, page: Page = None) -> Change:
        return self.insert_child(arrow_, page)

    def update_arrow(self, arrow_: Arrow) -> Change:
        old_arrow = self.find_one(gid=arrow_.gid())
        if not old_arrow:
            raise Exception('Can not update missing arrow')

        change = self.update_one(arrow_)
        if self.raw_entity_changes_channel:
            self.raw_entity_changes_channel.push(change)
        return change

    def remove_arrow(self, arrow_: Arrow) -> Change:
        change = self.remove_one(arrow_)
        if self.raw_entity_changes_channel:
            self.raw_entity_changes_channel.push(change)
        return change

    def arrows(self, page_: Page | str):
        page_gid = page_.gid() if isinstance(page_, Page) else page_
        return self.find(parent_gid=page_gid, type=Arrow)

    def arrow(self, page_: Page | str, arrow_id: str):
        page_gid = page_.gid() if isinstance(page_, Page) else page_
        return self.find_one(gid=(page_gid, arrow_id))

    # Other
    def apply_change(self, change: Change):
        last_state = change.last_state()

        if change.is_create():
            self.insert_one(last_state)
        elif change.is_update():
            self.update_one(last_state)
        elif change.is_delete():
            self.remove_one(last_state)

        if self.raw_entity_changes_channel:
            self.raw_entity_changes_channel.push(change)

    def write_to_disk(self):
        # TODO: This should be redundant when I implement the
        # Persistence Manager
        pass

    def default_page(self):
        return self.page(self.default_page_id)

    def set_default_page(self, new_page: Page):
        self.default_page_id = new_page.id
