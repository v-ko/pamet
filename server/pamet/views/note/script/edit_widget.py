from fusion.libs.state import view_state_type
from pamet.model.script_note import ScriptNote
from pamet.note_view_lib import register_note_view_type
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.views.note.base_edit.widget import BaseNoteEditWidget
from pamet.views.note.script.props_widget import ScriptNotePropsWidget


@view_state_type
class ScriptNoteEditViewState(NoteEditViewState, ScriptNote):
    pass


@register_note_view_type(state_type=ScriptNoteEditViewState,
                         note_type=ScriptNote,
                         edit=True)
class ScriptNoteEditWidget(BaseNoteEditWidget):

    def __init__(self, parent, initial_state: ScriptNoteEditViewState):
        BaseNoteEditWidget.__init__(self, parent, initial_state)

        self.script_props_widget = ScriptNotePropsWidget(self)
        self.ui.centralAreaWidget.layout().addWidget(
            self.script_props_widget)
