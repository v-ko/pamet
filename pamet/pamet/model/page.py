import misli
from misli import Entity, wrap_and_register_entity_type


@wrap_and_register_entity_type
class Page(Entity):
    _name: str = ''  # TODO: remove. for simplicity is key. gid=(user,repo,id)

    @property
    def name(self):
        return self.id

    @name.setter
    def name(self, new_name):
        self.id = new_name

    def __repr__(self):
        return f'<Page id={self.id}>'

    def notes(self):
        return misli.find(parent_gid=self.gid())

    def note(self, note_id: str):
        return misli.find_one(gid=(self.gid(), note_id))
