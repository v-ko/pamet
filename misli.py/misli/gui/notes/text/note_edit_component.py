from misli.gui.component import Component


class TextNoteEditComponent(Component):
    def __init__(self, parent_id):
        Component.__init__(
            self, parent_id=parent_id, obj_class='TextEdit')
