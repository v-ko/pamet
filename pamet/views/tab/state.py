from dataclasses import field
from typing import List

from fusion.libs.state import view_state_type, ViewState
from pamet.model.note import Note
from pamet.views.map_page.state import MapPageViewState


@view_state_type
class TabViewState(ViewState):
    title: str = ''
    page_view_state: MapPageViewState = field(default=None)
    note_edit_view_state: ViewState = None
    search_bar_state: ViewState = None
    creating_note: Note = None

    left_sidebar_state: ViewState = None
    page_edit_view_state: ViewState = None

    navigation_history: List[str] = field(default_factory=list)
    current_nav_index: int = None
    previous_nav_index: int = None

    page_state_cache: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (f'<TabViewState title={self.title}>')

    def set_navigation_index(self, new_index: int):
        new_index = max(0, min(len(self.navigation_history) - 1, new_index))

        if new_index == self.current_nav_index:
            return

        self.previous_nav_index = self.current_nav_index
        self.current_nav_index = new_index

    def right_sidebar_is_open(self):
        return bool(self.page_edit_view_state)

    def left_sidebar_is_open(self):
        return bool(self.left_sidebar_state)

    def add_page_state_to_cache(self, page_state: MapPageViewState):
        self.page_state_cache[page_state.page_id] = page_state

    def page_state_from_cache(self, page_id: str) -> MapPageViewState:
        return self.page_state_cache.get(page_id, None)
