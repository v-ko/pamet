from PySide2.QtWidgets import QWidget, QShortcut
from PySide2.QtGui import QKeySequence
from PySide2.QtCore import Qt

from .ui_text_note_edit_component import Ui_TextNoteEditComponent
from .note_edit_component import TextNoteEditComponent
from .. import usecases
from misli import misli
from misli.core.primitives import Rectangle


class TextNoteEditQtComponent(QWidget, TextNoteEditComponent):
    def __init__(self, parent_id):
        TextNoteEditComponent.__init__(self, parent_id)
        QWidget.__init__(self)

        self.ui = Ui_TextNoteEditComponent()
        self.ui.setupUi(self)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcuts = [esc_shortcut]

        self.ui.ok_button.clicked.connect(self._handle_ok_click)
        esc_shortcut.activated.connect(self._handle_esc_shortcut)

        self.note_display_rect = Rectangle(0, 0, 300, 300)
        self.note_text = ''

    def update(self):
        display_rect = self.note_display_rect

        height = display_rect.height() + self.ui.ok_button.height()
        display_rect.setHeight(height)

        tab_component = misli.component(self.parent_id)

        top_left = tab_component.mapToGlobal(display_rect.topLeft().toPoint())
        display_rect.moveTopLeft(top_left)

        self.setGeometry(display_rect.to_QRectF().toRect())
        self.ui.textEdit.setPlainText(self.note_text)

    def _handle_ok_click(self):
        text = self.ui.textEdit.toPlainText()
        usecases.finish_editing_note(self.id, text=text)

    def _handle_esc_shortcut(self):
        usecases.finish_editing_note(self.id)
