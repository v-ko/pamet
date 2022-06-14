from PySide6.QtWidgets import QVBoxLayout, QWidget, QLineEdit, QLabel
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from misli.entity_library.change import Change

from misli.gui import ViewState, view_state_type
from misli.gui.utils.qt_widgets import bind_and_apply_state
from misli.gui.utils.qt_widgets.qtview import QtView
from misli.gui.view_library.view import View

import pamet
from pamet import actions


@view_state_type
class MapPagePropertiesViewState(ViewState):
    focused_prop: str = ''
    page_id: str = ''

    @property
    def page(self):
        return pamet.page(id=self.page_id)


class MapPagePropertiesWidget(QWidget, View):

    def __init__(self, tab_widget, initial_state):
        QWidget.__init__(self, parent=tab_widget)
        View.__init__(self, initial_state=initial_state)
        self.tab_widget = tab_widget
        self.name_line_edit = QLineEdit('', self)
        self.name_line_edit.textChanged.connect(
            self._handle_name_line_edit_text_changed)

        self.name_warning_label = QLabel('This should not be visible')
        self.name_warning_label.hide()
        self.name_warning_label.setStyleSheet(
            'QLabel {color : red; font-size: 8pt;}')

        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc_shortcut.activated.connect(
            lambda: actions.tab.close_right_sidebar(self.tab_widget.state()))

        # binding = first_key_binding_for_command(save_page_properties)
        # self.save_button = QPushButton(f'Save ({binding.key})')
        self.save_button = QPushButton('Save (Ctrl+S)')
        # self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._handle_save_button_click)
        self.delete_button = QPushButton(f'Delete page')
        self.delete_button.clicked.connect(self._handle_delete_button_click)
        self.delete_button.setStyleSheet('QButton {background-color: red;}')

        layout = QVBoxLayout()
        layout.addWidget(QLabel('Name: '))
        layout.addWidget(self.name_line_edit)
        layout.addWidget(self.name_warning_label)
        layout.addWidget(self.save_button)
        layout.addStretch()
        layout.addWidget(self.delete_button)
        self.setLayout(layout)

        bind_and_apply_state(self, initial_state, self.on_state_change)

    def on_state_change(self, change: Change):
        # Fill the prop fields with the respective values
        if change.updated.page_id:
            self.name_line_edit.setText(self.state().page.name)

        # Apply the field focus when specified
        if change.updated.focused_prop:
            if self.state().focused_prop == 'name':
                self.name_line_edit.selectAll()

    def _handle_delete_button_click(self):

        actions.map_page.delete_page(self.tab_widget.state(),
                                     self.state().page)
        actions.tab.close_right_sidebar(self.tab_widget.state())

    def _handle_save_button_click(self):
        state = self.state()
        page = state.page
        page.name = self.name_line_edit.text()
        actions.map_page.save_page_properties(page)
        actions.tab.close_right_sidebar(self.tab_widget.state())

    def _handle_name_line_edit_text_changed(self, new_text):
        # Check if the id is available and valid
        state = self.state()
        if new_text == state.page.name:
            self.name_warning_label.hide()
            self.save_button.setEnabled(True)
            return

        if pamet.page(name=new_text):
            self.name_warning_label.setText('Name already taken')
            self.name_warning_label.show()
            self.save_button.setEnabled(False)
            return

        self.save_button.setEnabled(True)
        self.name_warning_label.hide()
