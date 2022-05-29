from __future__ import annotations
from PySide6.QtCore import QRectF, QPointF, QSize, QPoint
from PySide6.QtWidgets import QTextEdit

import misli
from misli.gui.utils.qt_widgets.qtview import QtView
from pamet.constants import MIN_NOTE_HEIGHT, MIN_NOTE_WIDTH
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.views.note.base_edit.widget import BaseNoteEditWidget


log = misli.get_logger(__name__)


class TextNoteEditWidget(BaseNoteEditWidget, QtView):

    def __init__(self, parent, initial_state: NoteEditViewState):
        super().__init__(parent, initial_state)
        QtView.__init__(self,
                        initial_state=initial_state,
                        on_state_change=self.on_state_change)

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

        self.text_edit.setPlainText(initial_state.note.text)
        # self.text_edit.setFocus()

    # This shouldn't be specified explicitly IMO, but I couldn't find the bug
    def focusInEvent(self, event) -> None:
        # print(self.focusPolicy())  -> NoFocus. So why does it not give focus
        # to the text edit automatically.. ?
        self.text_edit.setFocus()

    def on_state_change(self, change):
        state: NoteEditViewState = change.last_state()
        if not state.note:
            return

        # if change.is_create():



        # display_rect = QRectF(*state.note.rect().as_tuple())
        # display_rect.moveCenter(
        #     QPointF(*state.display_position.as_tuple()))

        # display_rect = QRectF(*state.note.rect().as_tuple())
        # display_rect.moveCenter(QPointF(*state.display_position.as_tuple()))

        # height = display_rect.height() + self.ui.saveButton.height()
        # display_rect.setHeight(height)

        # tab_component = self.parent()

        # top_left = tab_component.mapToGlobal(display_rect.topLeft().toPoint())
        # display_rect.moveTopLeft(top_left)

        # self.text_edit.setGeometry(display_rect.toRect())
        # self.setGeometry(display_rect.toRect())

        # self.show()

    def on_text_change(self):
        self.state().edited_note.text = self.text_edit.toPlainText()
