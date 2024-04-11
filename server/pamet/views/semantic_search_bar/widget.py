
from pamet.views.search_bar.widget import SearchBarWidget
from fusion.libs.state import ViewState, view_state_type
import pamet


@view_state_type
class SemanticSearchBarWidgetState(ViewState):
    pass


class SemanticSearchBarWidget(SearchBarWidget):

    @property
    def search_service(self):
        return pamet.semantic_search_service()
