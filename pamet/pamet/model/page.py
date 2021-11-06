import misli
from misli import Entity, wrap_and_register_entity_type


@wrap_and_register_entity_type
class Page(Entity):
    _name: str = ''

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        self._name = new_name

    def __repr__(self):
        return f'<Page id={self.id} name={self.name}>'

    def notes(self):
        return misli.find(parent_gid=self.gid())

    def note(self, note_id: str):
        return misli.find_one(gid=(self.gid(), note_id))
