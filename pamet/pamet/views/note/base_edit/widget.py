from __future__ import annotations
import json
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QMessageBox, QWidget

import misli.entity_library
from pamet.actions import note as note_actions
from pamet.views.note.base_edit.view_state import NoteEditViewState

from .ui_widget import Ui_BaseNoteEditWidget


class BaseNoteEditWidget(QWidget):

    def __init__(self, parent: TabWidget, initial_state: NoteEditViewState):
        QWidget.__init__(self, parent=parent)

        if initial_state.new_note_dict:
            type_name = initial_state.new_note_dict.pop('type_name')
            self.edited_note = misli.entity_library.from_dict(
                type_name, initial_state.new_note_dict)
        else:
            self.edited_note = initial_state.get_note()

            if not self.edited_note:
                raise Exception

        self.ui = Ui_BaseNoteEditWidget()
        self.ui.setupUi(self)

        QShortcut(QKeySequence(Qt.Key_Escape), self, self._handle_esc_shortcut)
        self.ui.saveButton.clicked.connect(self._handle_ok_click)
        self.ui.devButton.clicked.connect(self._handle_dev_button_click)

        page_view: MapPageWidget = parent.page_view()
        page_view_state = page_view.state()

        size = initial_state.rect().size()
        center = page_view_state.project_point(initial_state.rect().center())
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

    # @property
    # def note(self) -> Note:
    #     return self.state().note.copy()

    def _handle_esc_shortcut(self):
        note_actions.abort_editing_note(self.parent().state())

    def _handle_ok_click(self):
        # note.text = self.ui.textEdit.toPlainText().strip()

        if self.state().create_mode:
            note_actions.finish_creating_note(self.parent().state(),
                                              self.edited_note)
        else:
            note_actions.finish_editing_note(self.parent().state(),
                                             self.edited_note)

    def _handle_dev_button_click(self):
        note = self.state().get_note()
        QMessageBox.information(
            self,
            'Note info',
            json.dumps(note.asdict(), indent=4),
            # buttons=QMessageBox.Ok,
        )
