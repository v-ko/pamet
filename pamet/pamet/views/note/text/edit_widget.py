from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QTextEdit

import misli
from misli.gui.utils.qt_widgets import bind_and_apply_state
from misli.gui.utils.qt_widgets.qtview import QtView
from misli.gui.view_library.view import View
from pamet import register_note_view_type
from pamet.desktop_app import trash_icon, link_icon
from pamet.model.anchor_note import AnchorNote
from pamet.model.text_note import TextNote
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.views.note.base_edit.widget import BaseNoteEditWidget
from pamet.actions import map_page as map_page_actions

log = misli.get_logger(__name__)


class TextEditViewState(NoteEditViewState, TextNote):
    pass


@register_note_view_type(state_type=TextEditViewState,
                         note_type=TextNote,
                         edit=True)
class TextNoteEditWidget(BaseNoteEditWidget, View):

    def __init__(self, parent, initial_state: NoteEditViewState):
        super().__init__(parent, initial_state)
        View.__init__(self, initial_state=initial_state)

        self.text_edit: QTextEdit = QTextEdit(parent=self)

        # There's some shitty detail in the QTextEdit implementation where
        # there's a hidden min-height in some scroll area abstraction or
        # whatever. Does not warrant the time to debug ATM

        # self.text_edit.setFixedHeight(MIN_NOTE_HEIGHT)
        # self.text_edit.setMinimumHeight(MIN_NOTE_HEIGHT)
        # self.text_edit.setMaximumHeight(100)
        # self.text_edit.setContentsMargins(0,0,0,0)
        # self.text_edit.setFixedSize(QSize(MIN_NOTE_WIDTH, MIN_NOTE_HEIGHT))
        # self.text_edit.resize(QSize(MIN_NOTE_WIDTH, MIN_NOTE_HEIGHT))
        # self.text_edit.setSizePolicy()

        self.ui.centralAreaWidget.layout().addWidget(self.text_edit)
        self.text_edit.textChanged.connect(self.on_text_change)

        self.text_edit.setPlainText(initial_state.text)

        link_button = QPushButton(link_icon, '', self)
        link_button.setCheckable(True)
        trash_button = QPushButton(trash_icon, '', self)
        self.ui.toolbarLayout.addWidget(link_button)
        self.ui.toolbarLayout.addWidget(trash_button)
        link_button.toggled.connect(self.handle_link_button_toggled)

    # This shouldn't be specified explicitly IMO, but I couldn't find the bug
    def focusInEvent(self, event) -> None:
        # print(self.focusPolicy())  -> NoFocus. So why does it not give focus
        # to the text edit automatically.. ?
        self.text_edit.setFocus()

    def on_text_change(self):
        self.edited_note.text = self.text_edit.toPlainText()

    def handle_link_button_toggled(self, checked):
        if not checked:
            raise Exception('Should only be unchecked in a text note edit')
        # note = self.edited_note
        note = AnchorNote(**self.edited_note.asdict())

        map_page_actions.switch_note_type(self.parent().state(),
                                          note)
