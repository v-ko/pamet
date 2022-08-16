from dataclasses import field
from datetime import datetime
from misli import Entity, entity_type
import pamet
from pamet.helpers import Url, current_time
from pamet.model.arrow import Arrow
from pamet.model.note import Note


@entity_type
class Page(Entity):
    name: str = ''
    created: datetime = field(default_factory=current_time)
    modified: datetime = field(default_factory=current_time)

    def __repr__(self):
        return f'<Page id={self.id} name={self.name}>'

    def notes(self):
        return (entity for entity in pamet.find(parent_gid=self.gid())
                if isinstance(entity, Note))

    def note(self, note_id: str):
        return pamet.find_one(gid=(self.gid(), note_id))

    def arrows(self):
        return (entity for entity in pamet.find(parent_gid=self.gid())
                if isinstance(entity, Arrow))

    def arrow(self, note_id: str):
        return pamet.find_one(gid=(self.gid(), note_id))

    def url(self):
        return Url(f'pamet:///p/{self.id}')
