from misli.entities import Note
from misli.gui.base_component import Component


class NoteComponent(Component):
    def __init__(self, parent_id, obj_class):
        Component.__init__(self, parent_id, obj_class=obj_class)

        self._note_props = {}

    def note(self):
        return Note(**self._note_props)

    def set_props_from_note(self):
        raise NotImplementedError

    def set_props_from_entity(self, **entity):
        self._note_props = entity
        self.set_props_from_note()
