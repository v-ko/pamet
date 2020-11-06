from misli.objects.base_object import BaseObject
# from misli.objects.state import State


class Page(BaseObject):
    def __init__(self, **kwargs):
        note_list = kwargs.pop('notes', [])
        self._notes = {n.id: n for n in note_list}

        super(Page, self).__init__(obj_type='Page', **kwargs)

    def note(self, id):
        return self._notes[id]

    def notes(self):
        return [note for nid, note in self._notes.items()]
