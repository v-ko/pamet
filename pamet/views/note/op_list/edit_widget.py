from __future__ import annotations

from pamet.model.op_list_note import OtherPageListNote
from pamet.note_view_lib import register_note_view_type
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.views.note.base_edit.widget import BaseNoteEditWidget


@register_note_view_type(state_type=NoteEditViewState,
                         note_type=OtherPageListNote,
                         edit=True)
class OtherPageListNoteEditWidget(BaseNoteEditWidget):
    pass
