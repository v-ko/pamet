from fusion.libs.entity.change import Change
from fusion.libs.channel import Subscription
from pamet import channels
import pamet
from pamet.actions import note as note_actions
from pamet.desktop_app.util import elide_text
from pamet.util.url import Url


class LinkNoteViewMixin:

    def __init__(self):
        self._page_subscription: Subscription = None

    def recalculate_elided_text(self):
        state = self.state()
        url: Url = state.url
        if url.is_internal():
            page = pamet.page(url.get_page_id())
            if page:
                self._elided_text_layout = elide_text(page.name,
                                                      state.text_rect(),
                                                      self.font())
            else:
                self._elided_text_layout = elide_text('(missing)',
                                                      state.text_rect(),
                                                      self.font())
        else:  # Is not internal
            self._elided_text_layout = elide_text(state.text,
                                                  state.text_rect(),
                                                  self.font())

    def connect_to_page_changes(self, page_id):
        if self._page_subscription:
            self.disconnect_from_page_changes()

        self._page_subscription = channels.entity_changes_by_id.subscribe(
            self.handle_page_change, index_val=page_id)

    def disconnect_from_page_changes(self):
        if self._page_subscription:
            self._page_subscription.unsubscribe()
            self._page_subscription = None

    def handle_page_change(self, change: Change):
        if change.is_delete() or change.updated.name:
            note_actions.apply_page_change_to_anchor_view(self.state())
