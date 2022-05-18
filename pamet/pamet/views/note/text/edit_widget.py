from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt, QRectF, QPointF

import misli
from misli.gui.utils.qt_widgets.qtview import QtView
from pamet.actions import note as note_actions
from pamet.model.note import Note
from pamet.views.note.text.edit_view import TextNoteEditViewState
from pamet.views.note.text.ui_edit_widget import Ui_TextNoteEditViewWidget

log = misli.get_logger(__name__)


class TextNoteEditWidget(QWidget, QtView):
    def __init__(self, parent, initial_state):
        QWidget.__init__(self, parent=parent)
        QtView.__init__(self,
                        initial_state=initial_state,
                        on_state_change=self.on_state_change)

        self.ui = Ui_TextNoteEditViewWidget()
        self.ui.setupUi(self)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.ui.ok_button.clicked.connect(self._handle_ok_click)
        esc_shortcut.activated.connect(self._handle_esc_shortcut)

        self.show()

    @property
    def note(self) -> Note:
        return self.state().note.copy()

    def _handle_esc_shortcut(self):
        note_actions.abort_editing_note(self.parent().state())

    def on_state_change(self, change):
        state: TextNoteEditViewState = change.last_state()
        if not state.note:
            return

        display_rect = QRectF(*state.note.rect().as_tuple())
        display_rect.moveCenter(
            QPointF(*state.display_position.as_tuple()))

        height = display_rect.height() + self.ui.ok_button.height()
        display_rect.setHeight(height)

        tab_component = self.parent()

        top_left = tab_component.mapToGlobal(display_rect.topLeft().toPoint())
        display_rect.moveTopLeft(top_left)

        self.setGeometry(display_rect.toRect())
        self.ui.textEdit.setPlainText(self.note.text)
        self.show()

    def _handle_ok_click(self):
        note = self.note
        note.text = self.ui.textEdit.toPlainText().strip()

        if self.state().create_mode:
            note_actions.finish_creating_note(self.parent().state(), note)
        else:
            note_actions.finish_editing_note(self.parent().state(), note)
