from __future__ import annotations
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QWidget
from pamet.model.note import Note
from pamet.actions import note as note_actions

from .ui_widget import Ui_BaseNoteEditWidget


class BaseNoteEditWidget(QWidget):

    def __init__(self, parent: TabWidget, initial_state):
        QWidget.__init__(self, parent=parent)

        self.ui = Ui_BaseNoteEditWidget()
        self.ui.setupUi(self)

        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.ui.saveButton.clicked.connect(self._handle_ok_click)
        esc_shortcut.activated.connect(self._handle_esc_shortcut)

        page_view: MapPageWidget = parent.page_view()
        page_view_state = page_view.state()

        size = initial_state.note.rect().size()
        center = page_view_state.project_point(
            initial_state.note.rect().center())
        center = page_view.mapToGlobal(QPoint(*center.as_tuple()))

        # Center the widget on the note with a size
        self_rect = self.geometry()
        delta_y = self.ui.bottomLayout.geometry().size().height()
        delta_y += self.ui.topLayout.geometry().size().height()
        size = QSize(*size.as_tuple())
        size.setHeight(size.height() + delta_y)
        self_rect.setSize(size)
        self_rect.moveCenter(center)
        self.setGeometry(self_rect)

    @property
    def note(self) -> Note:
        return self.state().note.copy()

    def _handle_esc_shortcut(self):
        note_actions.abort_editing_note(self.parent().state())

    def _handle_ok_click(self):
        note = self.note
        # note.text = self.ui.textEdit.toPlainText().strip()

        if self.state().create_mode:
            note_actions.finish_creating_note(self.parent().state(), note)
        else:
            note_actions.finish_editing_note(self.parent().state(), note)
