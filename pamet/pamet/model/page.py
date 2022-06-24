from misli import Entity, entity_type
import pamet
from pamet.model.arrow import Arrow
from pamet.model.note import Note


@entity_type
class Page(Entity):
    name: str = ''

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
