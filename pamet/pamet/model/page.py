from misli import Entity, entity_type
import pamet


@entity_type
class Page(Entity):
    name: str = ''

    def __repr__(self):
        return f'<Page id={self.id} name={self.name}>'

    def notes(self):
        return pamet.find(parent_gid=self.gid())

    def note(self, note_id: str):
        return pamet.find_one(gid=(self.gid(), note_id))
