from misli.objects.base_object import BaseObject
from misli.objects.note import Note
# from misli.objects.state import State


class Page(BaseObject):
    def __init__(self, **page_state):
        note_states = page_state.pop('note_states', [])
        obj_type = page_state.pop('obj_type', 'Page')

        super(Page, self).__init__(obj_type=obj_type, **page_state)

        self._notes = {}

        if note_states:
            for ns in note_states:
                self.add_note(Note(**ns))

    def note(self, id):
        return self._notes[id]

    def notes(self):
        return [note for nid, note in self._notes.items()]

    def add_note(self, note):
        self._notes[note.id] = note

    def remove_note(self, note):
        del self._notes[note.id]

    def state(self, include_notes=False):
        self_state = super().state()
        self_state['note_states'] = [n.state() for n in self.notes()]
        return self_state
