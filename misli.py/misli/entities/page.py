from misli.entities.base_entity import BaseEntity
from misli.entities.note import Note
from misli import get_logger
log = get_logger(__name__)


class Page(BaseEntity):
    def __init__(self, **page_state):
        id = page_state.pop('id', None)
        obj_class = page_state.pop('obj_class', None)

        BaseEntity.__init__(
            self, id=id, obj_type='Page', obj_class=obj_class)

        self._note_states = page_state.get('note_states', {})
        self.name = page_state.get('name', '')

        self.add_state_keys(['name', 'note_states'])

    def note(self, id):
        return Note(**self.note_states[id])

    def notes(self):
        return [self.note(nid) for nid in self.note_states]

    @property
    def note_states(self):
        return self._note_states

    @note_states.setter
    def note_states(self, new_states):
        self._note_states = new_states

    def add_note(self, note):
        if note.page_id != self.id:
            raise Exception(
                'Note id different from my id: "%s".' % note.page_id)

        self._note_states[note.id] = note.state()

    def remove_note(self, note):
        del self._note_states[note.id]

    def update_note(self, note):
        self._note_states[note.id] = note.state()
