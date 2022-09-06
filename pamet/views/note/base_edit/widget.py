from __future__ import annotations
import json
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QMessageBox, QPushButton, QWidget

from fusion.libs.entity import load_from_dict
from fusion.view import View
from fusion.platform.qt_widgets.views.context_menu.widget import ContextMenuWidget
from pamet.actions import note as note_actions
from pamet.note_view_lib import note_types_with_assiciated_views
from pamet.views.map_page.widget import MapPageWidget
from pamet.views.note.base_edit.view_state import NoteEditViewState
from pamet.desktop_app import icons

from .ui_widget import Ui_BaseNoteEditWidget


class BaseNoteEditWidget(QWidget, View):

    def __init__(self, parent: TabWidget, initial_state: NoteEditViewState):
        QWidget.__init__(self, parent=parent)
        View.__init__(self, initial_state=initial_state)
        self.parent_tab: TabWidget = parent

        if initial_state.new_note_dict:
            self.edited_note = load_from_dict(
                initial_state.new_note_dict)
        else:
            self.edited_note = initial_state.get_note()

            if not self.edited_note:
                raise Exception

        self.ui = Ui_BaseNoteEditWidget()
        self.ui.setupUi(self)

        trash_button = QPushButton(icons.trash, '', self)
        self.ui.toolbarLayout.addWidget(trash_button)

        self.switch_type_button = QPushButton(icons.more, '', self)
        self.ui.toolbarLayout.addWidget(self.switch_type_button)

        QShortcut(QKeySequence(Qt.Key_Escape), self, self._handle_esc_shortcut)
        self.ui.saveButton.clicked.connect(self._handle_ok_click)
        self.ui.devButton.clicked.connect(self._handle_dev_button_click)
        self.ui.cancelButton.clicked.connect(
            lambda: note_actions.abort_editing_note(self.parent_tab.state()))
        trash_button.clicked.connect(
            lambda: note_actions.abort_editing_and_delete_note(self.parent_tab.
                                                               state()))
        self.switch_type_button.clicked.connect(
            self._show_the_type_switch_menu)

        page_view: MapPageWidget = parent.page_view()
        page_view_state = page_view.state()

        # Center the widget over the note being edited with a size possibly
        # the same as the notes unscaled size
        size = initial_state.rect().size()
        center = page_view_state.project_point(initial_state.rect().center())
        center = page_view.mapToGlobal(QPoint(*center.as_tuple()))

        self_rect = self.geometry()
        delta_y = self.ui.bottomLayout.geometry().size().height()
        delta_y += self.ui.topLayout.geometry().size().height()
        size = QSize(*size.as_tuple())
        size.setHeight(size.height() + delta_y)
        self_rect.setSize(size)
        self_rect.moveCenter(center)
        self.setGeometry(self_rect)

    def _handle_esc_shortcut(self):
        note_actions.abort_editing_note(self.parent_tab.state())

    def _handle_ok_click(self):
        if self.state().create_mode:
            note_actions.finish_creating_note(self.parent_tab.state(),
                                              self.edited_note)
        else:
            note_actions.finish_editing_note(self.parent_tab.state(),
                                             self.edited_note)

    def _handle_dev_button_click(self):
        note = self.state().get_note()
        if note:
            note_dict_str = json.dumps(note.asdict(),
                                       indent=4,
                                       ensure_ascii=False)
        else:
            note_dict_str = 'Creating new note, no info'
        QMessageBox.information(
            self,
            'Note info',
            note_dict_str,
            # buttons=QMessageBox.Ok,
        )

    def _show_the_type_switch_menu(self):
        switch_type_menu_entries = {}
        for NoteType in note_types_with_assiciated_views():

            def command(NoteType=NoteType):
                # Possibly ask for a scripts permission here
                note_actions.switch_note_type(
                    self.parent_tab.state(),
                    NoteType.create_silent(**self.edited_note.asdict()))

            switch_type_menu_entries[NoteType.__name__] = command

        menu_dict = {'Switch type:': None, **switch_type_menu_entries}
        menu = ContextMenuWidget(self, menu_dict)

        # Center the menu under the button and show it
        position = self.switch_type_button.rect().center()
        position.setX(position.x() - menu.width() / 2)
        menu.popup(position)
