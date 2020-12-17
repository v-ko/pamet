from PySide2.QtWidgets import QWidget, QShortcut
from PySide2.QtGui import QKeySequence
from PySide2.QtCore import Qt

from .ui_edit_component import Ui_TextNoteEditComponent
from .edit_component import TextNoteEditComponent

import misli
log = misli.get_logger(__name__)


class TextNoteEditQtComponent(QWidget, TextNoteEditComponent):
    def __init__(self, parent_id):
        TextNoteEditComponent.__init__(self, parent_id)
        QWidget.__init__(self)

        self.ui = Ui_TextNoteEditComponent()
        self.ui.setupUi(self)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)

        self.ui.ok_button.clicked.connect(self._handle_ok_click)
        esc_shortcut.activated.connect(self._handle_esc_shortcut)

    def update(self):
        log.info('EditComponent update')
        display_rect = self.note.rect().to_QRectF()
        display_rect.moveCenter(self.display_position.to_QPointF())

        height = display_rect.height() + self.ui.ok_button.height()
        display_rect.setHeight(height)

        tab_component = misli.gui.component(self.parent_id)

        top_left = tab_component.mapToGlobal(display_rect.topLeft().toPoint())
        display_rect.moveTopLeft(top_left)

        self.setGeometry(display_rect.toRect())
        self.ui.textEdit.setPlainText(self.note.text)
        self.show()

    def _handle_ok_click(self):
        self.note.text = self.ui.textEdit.toPlainText()
        TextNoteEditComponent._handle_ok_click(self)
