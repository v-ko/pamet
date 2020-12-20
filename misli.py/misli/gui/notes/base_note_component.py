from misli.entities import Note
from misli.gui.base_component import Component


class NoteComponent(Component):
    def __init__(self, parent_id, obj_class):
        Component.__init__(self, parent_id, obj_class=obj_class)

        self._note_props = None

    def note(self):
        if self._note_props:
            return Note(**self._note_props)

    def set_props_from_note(self):
        raise NotImplementedError

    def set_props_from_base_object(self, **base_object):
        self._note_props = base_object
        self.set_props_from_note()
