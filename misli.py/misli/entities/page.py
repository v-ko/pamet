from misli.entities.base_entity import BaseEntity
from misli.entities.note import Note
from misli import get_logger
log = get_logger(__name__)


class Page(BaseEntity):
    def __init__(self, **page_state):
        id = page_state.pop('id', None)
        obj_type = page_state.pop('obj_type', 'Page')
        obj_class = page_state.pop('obj_class', None)

        BaseEntity.__init__(
            self, id=id, obj_type=obj_type, obj_class=obj_class)

        self._notes = {}
        self.name = ''

        self.add_state_keys(['name'])

        note_states = page_state.pop('note_states', [])
        if note_states:
            for ns in note_states:
                self.add_note(Note(**ns))

    def note(self, id):
        return self._notes[id]

    def notes(self):
        return [note for nid, note in self._notes.items()]

    def add_note(self, note):
        if note.page_id != self.id:
            raise Exception(
                'Note id different from my id: "%s".' % note.page_id)

        self._notes[note.id] = note

    def remove_note(self, note):
        del self._notes[note.id]

    def state(self, include_notes=False):
        self_state = super().state()
        self_state['note_states'] = []

        if include_notes:
            for nt in self.notes():
                nt_state = nt.state()
                self_state['note_states'].append(nt_state)

        return self_state
