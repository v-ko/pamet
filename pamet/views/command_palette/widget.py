from PySide6.QtCore import Qt
from PySide6.QtGui import QFocusEvent, QKeyEvent, QResizeEvent
from PySide6.QtWidgets import QListWidgetItem, QWidget
from fusion.view import View
import pamet

from thefuzz import process

from fusion.libs.command import commands
from fusion.libs.state import ViewState, view_state_type
from pamet.actions import tab as tab_actions
from pamet.actions import window as window_actions
from .ui_widget import Ui_CommandPaletteWidget


@view_state_type
class CommandPaletteViewState(ViewState):
    line_edit_text: str = ''


class CommandPaletteWidget(QWidget, View):

    def __init__(self, parent, initial_state: CommandPaletteViewState):
        QWidget.__init__(self, parent)
        View.__init__(self, initial_state)

        self.ui = Ui_CommandPaletteWidget()
        self.ui.setupUi(self)

        self.ui.lineEdit.setText(initial_state.line_edit_text)
        self.ui.lineEdit.textChanged.connect(self._handle_text_change)
        self.ui.lineEdit.setFocus()
        self.setMinimumHeight(self.ui.lineEdit.geometry().height())

        self.ui.suggestionsListWidget.itemActivated.connect(
            self._handle_item_activated)
        # # Close on Esc shortcut - moved to the Window.handle_esc_shortcut

        # Do the initial reuslts display
        self._handle_text_change(initial_state.line_edit_text)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        window_actions.close_command_view(self.parent().state())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        list_widget = self.ui.suggestionsListWidget
        if event.key() == Qt.Key_Up:
            list_widget.setCurrentRow(max(0, list_widget.currentRow() - 1))
        elif event.key() == Qt.Key_Down:
            list_widget.setCurrentRow(
                min(list_widget.count(),
                    list_widget.currentRow() + 1))
        elif event.key() == Qt.Key_Return:
            self._handle_item_activated(list_widget.currentItem())
        else:
            return super().keyPressEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.adjustSize()
        return super().resizeEvent(event)

    def _handle_text_change(self, new_text: str):
        self.ui.suggestionsListWidget.clear()

        if new_text.startswith('>'):  # Show commands
            search_string = new_text[1:]
            choices_dict = {c: c.title for c in commands()}
            results = process.extract(search_string,
                                      choices=choices_dict,
                                      limit=None)

            for title, score, command in results:
                # if score
                item = QListWidgetItem(title)
                item.setData(Qt.UserRole, command)
                self.ui.suggestionsListWidget.addItem(item)

        else:  # No special prefix - show files to Go to
            choices_dict = {p.id: p.name for p in pamet.pages()}
            results = process.extract(new_text,
                                      choices=choices_dict,
                                      limit=None)

            tab = self.parent().current_tab()
            current_page = pamet.page(tab.state().page_view_state.page_id)

            for name, score, page_id in results:
                if page_id == current_page.id:
                    continue

                item = QListWidgetItem(name)
                page = pamet.page(page_id).copy()
                if not tab:
                    item.setData(Qt.UserRole,
                                 lambda p=page: window_actions.new_browser_tab(
                                     self.parent().state(), p))
                else:
                    item.setData(Qt.UserRole,
                                 lambda p=page: tab_actions.go_to_url(
                                     tab.state(), p.url()))

                self.ui.suggestionsListWidget.addItem(item)

        self.ui.suggestionsListWidget.setCurrentRow(0)
        self.adjustSize()

    def _handle_item_activated(self, item):
        if not item:
            window_actions.close_command_view(self.parent().state())
            return

        # Call the corresponding method (stored as item data)
        command = item.data(Qt.UserRole)
        window_actions.close_command_view(self.parent().state())
        command()
