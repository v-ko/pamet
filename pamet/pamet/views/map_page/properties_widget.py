from PySide6.QtWidgets import QVBoxLayout, QWidget, QLineEdit, QLabel
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

import misli
from misli.gui.key_binding_manager import first_key_binding_for_command
from misli.gui import ViewState, wrap_and_register_view_state_type
from misli.gui import View, register_view_type

import pamet
from pamet.model import Page
from pamet.actions import map_page as map_page_actions
from pamet.commands import save_page_properties


@wrap_and_register_view_state_type
class MapPagePropertiesViewState(ViewState):
    focused_prop: str = None

    @property
    def page(self):
        return self.mapped_entity


@register_view_type(priority=-1, entity_type=Page.__name__, page_edit=True)
class MapPagePropertiesWidget(QWidget, View):
    def __init__(self, parent_id):
        parent = misli.gui.view(parent_id)
        QWidget.__init__(self, parent=parent)
        View.__init__(self,
                      parent_id,
                      initial_state=MapPagePropertiesViewState())

        self.name_line_edit = QLineEdit('', self)
        self.name_line_edit.textChanged.connect(
            self._handle_name_line_edit_text_changed)

        self.name_warning_label = QLabel('This should not be visible')
        self.name_warning_label.hide()
        self.name_warning_label.setStyleSheet(
            'QLabel {color : red; font-size: 8pt;}')

        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc_shortcut.activated.connect(
            lambda: map_page_actions.close_page_properties(self.id))

        binding = first_key_binding_for_command(save_page_properties)
        self.save_button = QPushButton(f'Save ({binding.key})')
        # self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._handle_save_button_click)
        self.delete_button = QPushButton(f'Delete page')
        self.delete_button.clicked.connect(
            lambda: map_page_actions.delete_page(self.parent_id,
                                                 self.state().page))
        self.delete_button.setStyleSheet('QButton {background-color: red;}')

        layout = QVBoxLayout()
        layout.addWidget(QLabel('Name: '))
        layout.addWidget(self.name_line_edit)
        layout.addWidget(self.name_warning_label)
        layout.addWidget(self.save_button)
        layout.addStretch()
        layout.addWidget(self.delete_button)
        self.setLayout(layout)

    def on_state_update(self):
        # Fill the prop fields with the respective values
        state = self.state()
        previous_state = self.previous_state()
        page = state.page
        if previous_state.page != state.page:
            self.name_line_edit.setText(page.name)

        # Apply the field focus when specified
        if previous_state.focused_prop != state.focused_prop:
            if self.state().focused_prop == 'name':
                self.name_line_edit.selectAll()

    def _handle_save_button_click(self):
        state = self.state()
        page = state.page
        page.name = self.name_line_edit.text()
        map_page_actions.save_page_properties(page)
        map_page_actions.close_page_properties(self.id)

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
