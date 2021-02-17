from misli.dataclasses import dataclass, Entity
from misli_gui.base_component import Component
from pamet.entities import Note


@dataclass
class NoteComponentState(Entity):
    note: Note = None


class NoteComponent(Component):
    def __init__(self, obj_class, parent_id):
        Component.__init__(
            self,
            parent_id=parent_id,
            default_state=NoteComponentState(),
            obj_class=obj_class
        )

    @property
    def note(self):
        return self.state().note.copy()
