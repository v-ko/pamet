from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt, QRectF, QPointF

from misli import gui
from misli.gui.view_library import register_view_class

from pamet.note_components.text.edit_view import TextNoteEditView
from pamet.note_components.text.ui_edit_widget import Ui_TextNoteEditViewWidget

from pamet.note_components import usecases

import misli
log = misli.get_logger(__name__)


@register_view_class(obj_type='TextNote', edit=True)
class TextNoteEditViewWidget(QWidget, TextNoteEditView):
    def __init__(self, parent_id):
        TextNoteEditView.__init__(self, parent_id)
        QWidget.__init__(self)

        self.ui = Ui_TextNoteEditViewWidget()
        self.ui.setupUi(self)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)

        self.ui.ok_button.clicked.connect(self._handle_ok_click)
        esc_shortcut.activated.connect(self._handle_esc_shortcut)

    def handle_model_update(self, old_state, new_state):
        self.update()

    def update(self):
        log.info('EditComponent update')
        display_rect = QRectF(*self.note.rect().to_list())
        display_rect.moveCenter(QPointF(*self.displayed_model.display_position.to_list()))

        height = display_rect.height() + self.ui.ok_button.height()
        display_rect.setHeight(height)

        tab_component = gui.view(self.parent_id)

        top_left = tab_component.mapToGlobal(display_rect.topLeft().toPoint())
        display_rect.moveTopLeft(top_left)

        self.setGeometry(display_rect.toRect())
        self.ui.textEdit.setPlainText(self.note.text)
        self.show()

    def _handle_ok_click(self):
        text = self.ui.textEdit.toPlainText()
        note = self.note
        note.text = text.strip()

        if self.displayed_model.create_mode:
            usecases.finish_creating_note(self.id, note)
        else:
            usecases.finish_editing_note(self.id, note)