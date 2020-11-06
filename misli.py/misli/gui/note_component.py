from misli import misli
from misli.objects.base_object import BaseObject


class NoteComponent(BaseObject):
    def __init__(self, page_id, note_id):
        BaseObject.__init__(
            self,
            obj_type='NoteComponent',
            _page_id=page_id,
            _note_id=note_id)
        # self._page_id = page_id
        # self._note_id = note_id

        misli.add_component(self)

    def note(self):
        note = misli.page(self._page_id).note(self._note_id)
        return note

    def set_state(self, new_state):
        raise NotImplementedError
