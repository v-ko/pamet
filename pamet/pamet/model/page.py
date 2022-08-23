from dataclasses import field
from datetime import datetime
from misli import Entity, entity_type
from misli.entity_library.change import Change
from misli.storage.repository import Repository
import pamet
from pamet.helpers import Url
from misli.helpers import current_time
from pamet.model.arrow import Arrow
from pamet.model.note import Note


@entity_type
class Page(Entity):
    parent_repository: Repository = field(default=None, repr=False)
    name: str = ''
    created: datetime = field(default_factory=current_time)
    modified: datetime = field(default_factory=current_time)

    def __repr__(self):
        return f'<Page gid={self.gid()} name={self.name}>'

    @property
    def repository(self):
        return self.parent_repository or pamet.sync_repo()

    def notes(self):
        return (entity
                for entity in self.repository.find(parent_gid=self.gid())
                if isinstance(entity, Note))

    def note(self, note_id: str):
        return self.repository.find_one(gid=(self.gid(), note_id))

    def arrows(self):
        return (entity
                for entity in self.repository.find(parent_gid=self.gid())
                if isinstance(entity, Arrow))

    def arrow(self, note_id: str):
        return self.repository.find_one(gid=(self.gid(), note_id))

    def url(self):
        return Url(f'pamet:///p/{self.id}')

    def insert_note(self, note: Note) -> Change:
        note.page_id = self.id
        return self.repository.insert_note(note)

    def insert_arrow(self, arrow: Arrow) -> Change:
        arrow.page_id = self.id
        return self.repository.insert_arrow(arrow)
