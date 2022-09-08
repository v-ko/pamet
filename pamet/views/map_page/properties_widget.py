from PySide6.QtWidgets import QMessageBox, QWidget
from fusion.libs.entity.change import Change

from fusion.libs.state import ViewState, view_state_type
from fusion.platform.qt_widgets import bind_and_apply_state
from fusion.view import View

import pamet
from pamet import actions
from pamet.model.page import Page
from .ui_properties_widget import Ui_MapPagePropertiesWidget


@view_state_type
class MapPagePropertiesViewState(ViewState):
    focused_prop: str = ''

    @property
    def page_id(self):
        return self.id


class MapPagePropertiesWidget(QWidget, View):

    def __init__(self, tab_widget, initial_state):
        QWidget.__init__(self, parent=tab_widget)
        View.__init__(self, initial_state=initial_state)

        self.ui = Ui_MapPagePropertiesWidget()
        self.ui.setupUi(self)

        self.parent_tab = tab_widget

        # Configure the UI
        # Set the home page check box state
        default_page = pamet.sync_repo().default_page()
        if default_page and default_page.id == initial_state.page_id:
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
            page = pamet.page(self.state().page_id)
            self.ui.nameLineEdit.setText(page.name)

        # Apply the field focus when specified
        if change.updated.focused_prop:
            if self.state().focused_prop == 'name':
                self.ui.nameLineEdit.selectAll()

    def _handle_delete_button_click(self):
        reply = QMessageBox.question(
            self, 'Delete page', 'Are you sure you want to delete the page?')
        if reply == QMessageBox.StandardButton.Yes:
            actions.map_page.delete_page(self.parent_tab.state(),
                                         pamet.page(self.state().page_id))
        actions.tab.close_page_properties(self.parent_tab.state())

    def _save_page(self):
        state = self.state()
        page = pamet.page(state.page_id)
        page.name = self.ui.nameLineEdit.text()
        actions.map_page.save_page_properties(page)
        actions.tab.close_page_properties(self.parent_tab.state())

    def _handle_name_line_edit_text_changed(self, new_text):
        # Check if the id is available and valid
        state = self.state()
        if new_text == pamet.page(state.page_id).name:
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
        if checked:
            home_page = pamet.page(self.state().page_id)
        else:
            home_page = None
        pamet.sync_repo().set_default_page(home_page)
