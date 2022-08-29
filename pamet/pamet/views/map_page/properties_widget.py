from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget, QLineEdit, QLabel
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from fusion.entity_library.change import Change

from fusion.gui import ViewState, view_state_type
from fusion.gui.utils.qt_widgets import bind_and_apply_state
from fusion.gui.view_library.view import View

import pamet
from pamet import actions
from pamet.desktop_app import get_config
from .ui_properties_widget import Ui_MapPagePropertiesWidget


@view_state_type
class MapPagePropertiesViewState(ViewState):
    focused_prop: str = ''
    page_id: str = ''

    def get_page(self):
        return pamet.page(self.page_id)


class MapPagePropertiesWidget(QWidget, View):

    def __init__(self, tab_widget, initial_state):
        QWidget.__init__(self, parent=tab_widget)
        View.__init__(self, initial_state=initial_state)

        self.ui = Ui_MapPagePropertiesWidget()
        self.ui.setupUi(self)

        self.parent_tab = tab_widget

        # Configure the UI
        # Set the home page check box state
        config = get_config()
        page = initial_state.get_page()
        if config.home_page_id == page.id:
            self.ui.setAsHomePageCheckBox.setChecked(True)

        self.ui.nameWarningLabel.hide()
        self.ui.nameWarningLabel.setStyleSheet(
            'QLabel {color : red; font-size: 8pt;}')

        # Bind UI signals to the appropriate methods
        self.ui.nameLineEdit.textChanged.connect(
            self._handle_name_line_edit_text_changed)

        self.ui.saveButton.clicked.connect(self._save_page)
        self.ui.setAsHomePageCheckBox.toggled.connect(
            self._handle_home_page_toggle)
        self.ui.deleteButton.clicked.connect(self._handle_delete_button_click)
        self.ui.deleteButton.setStyleSheet('QButton {background-color: red;}')

        bind_and_apply_state(self, initial_state, self.on_state_change)

    def on_state_change(self, change: Change):
        # Fill the prop fields with the respective values
        if change.updated.page_id:
            self.ui.nameLineEdit.setText(self.state().get_page().name)

        # Apply the field focus when specified
        if change.updated.focused_prop:
            if self.state().focused_prop == 'name':
                self.ui.nameLineEdit.selectAll()

    def _handle_delete_button_click(self):
        reply = QMessageBox.question(
            self, 'Delete page', 'Are you sure you want to delete the page?')
        if reply == QMessageBox.StandardButton.Yes:
            actions.map_page.delete_page(self.parent_tab.state(),
                                         self.state().get_page())
        actions.tab.close_right_sidebar(self.parent_tab.state())

    def _save_page(self):
        state = self.state()
        page = state.get_page()
        page.name = self.ui.nameLineEdit.text()
        actions.map_page.save_page_properties(page)
        actions.tab.close_right_sidebar(self.parent_tab.state())

    def _handle_name_line_edit_text_changed(self, new_text):
        # Check if the id is available and valid
        state = self.state()
        if new_text == state.get_page().name:
            self.ui.nameWarningLabel.hide()
            self.ui.saveButton.setEnabled(True)
            return

        if not new_text:
            self.ui.nameWarningLabel.setText('The page name can not be empty')
            self.ui.nameWarningLabel.show()
            self.ui.saveButton.setEnabled(False)
            return

        elif pamet.find_one(name=new_text, type=Page):
            self.ui.nameWarningLabel.setText('Name already taken')
            self.ui.nameWarningLabel.show()
            self.ui.saveButton.setEnabled(False)
            return

        self.ui.saveButton.setEnabled(True)
        self.ui.nameWarningLabel.hide()

    def _handle_home_page_toggle(self, checked: bool):
        config = get_config()
        page = self.state().get_page()

        if checked:
            config.home_page_id = page.id
        else:
            config.home_page_id = None
        pamet.save_config(config)
