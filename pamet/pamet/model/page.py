import misli
from misli import Entity, entity_type


@entity_type
class Page(Entity):
    name: str = ''

    def __repr__(self):
        return f'<Page id={self.id} name={self.name}>'

    def notes(self):
        return misli.find(parent_gid=self.gid())

    def note(self, note_id: str):
        return misli.find_one(gid=(self.gid(), note_id))
