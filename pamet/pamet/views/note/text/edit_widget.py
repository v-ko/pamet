from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt, QRectF, QPointF

import misli
from misli.gui.view_library import register_view_type
from pamet.actions import note as note_actions
from pamet.views.note.text.edit_view import TextNoteEditView
from pamet.views.note.text.edit_view import TextNoteEditViewState
from pamet.views.note.text.ui_edit_widget import Ui_TextNoteEditViewWidget

log = misli.get_logger(__name__)


@register_view_type(entity_type='TextNote', edit=True)
class TextNoteEditViewWidget(QWidget, TextNoteEditView):
    def __init__(self, parent_id):
        TextNoteEditView.__init__(self, parent_id)
        QWidget.__init__(self)

        self.ui = Ui_TextNoteEditViewWidget()
        self.ui.setupUi(self)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)

        self.ui.ok_button.clicked.connect(self._handle_ok_click)
        esc_shortcut.activated.connect(self._handle_esc_shortcut)

    def handle_state_update(self):
        self.update()

    def update(self):
        model: TextNoteEditViewState = self.state
        display_rect = QRectF(*self.note.rect().as_tuple())
        display_rect.moveCenter(
            QPointF(*model.display_position.as_tuple()))

        height = display_rect.height() + self.ui.ok_button.height()
        display_rect.setHeight(height)

        tab_component = misli.gui.view(self.parent_id)

        top_left = tab_component.mapToGlobal(display_rect.topLeft().toPoint())
        display_rect.moveTopLeft(top_left)

        self.setGeometry(display_rect.toRect())
        self.ui.textEdit.setPlainText(self.note.text)
        self.show()

    def _handle_ok_click(self):
        model: TextNoteEditViewState = self.state
        text = self.ui.textEdit.toPlainText()
        note = self.note
        note.text = text.strip()

        if model.create_mode:
            note_actions.finish_creating_note(self.id, note)
        else:
            note_actions.finish_editing_note(self.id, note)
