from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QListWidgetItem, QWidget

from fusion.libs.state import ViewState, view_state_type
import pamet
from pamet.util.url import Url
from pamet.services.search.base import SearchResult
from pamet.actions import tab as tab_actions

from .ui_widget import Ui_SearchBarWidget

MAX_RESULTS_COUNT = 1000


@view_state_type
class SearchBarWidgetState(ViewState):
    pass


class SearchItem(QListWidgetItem):

    def __init__(self, search_result: SearchResult):
        QListWidgetItem.__init__(self, search_result.content_string)
        self.setData(Qt.UserRole, search_result)
        # self.setBackground(Qt.gray)
        # self.setText(search_result.content_string)


class SearchBarWidget(QWidget):

    def __init__(self, parent, initial_state):
        QWidget.__init__(self, parent)

        self.parent_tab = parent

        self.ui = Ui_SearchBarWidget()
        self.ui.setupUi(self)

        self.ui.searchLineEdit.textChanged.connect(self.update_search_results)
        palette = self.palette()
        self.setStyleSheet(f"""QListWidget::item {{
                border-bottom: 1px solid {palette.mid().color().name()};
            }}""")

        self.ui.resultsListWidget.itemClicked.connect(
            self.handle_item_activated)

    def showEvent(self, event: QShowEvent):
        self.ui.searchLineEdit.setFocus()
        self.ui.searchLineEdit.selectAll()
        return super().showEvent(event)

    def update_search_results(self, search_text):
        self.ui.resultsListWidget.clear()

        if not search_text:
            return

        search_service = pamet.search_service()
        count = 0
        for result in search_service.text_search(search_text):
            self.ui.resultsListWidget.addItem(SearchItem(result))
            count += 1

            if count > MAX_RESULTS_COUNT:
                break

    def handle_item_activated(self, item: SearchItem):
        search_result: SearchResult = item.data(Qt.UserRole)
        note = search_result.get_note()
        page = pamet.page(note.page_id)

        url = Url(page.url()).with_anchor(note=note)
        url = str(url)
        tab_actions.go_to_url(self.parent_tab.state(), url)
