from fusion.entity_library.change import Change
from fusion.pubsub import Subscription
from pamet import channels
from pamet.actions import note as note_actions


class LinkNoteViewMixin:
    def __init__(self):
        self._page_subscription: Subscription = None

    def connect_to_page_changes(self, page):
        if self._page_subscription:
            self.disconnect_from_page_changes()

        self._page_subscription = channels.entity_changes_by_id.subscribe(
            self.handle_page_change, index_val=page.id)

    def disconnect_from_page_changes(self):
        if self._page_subscription:
            self._page_subscription.unsubscribe()
            self._page_subscription = None

    def handle_page_change(self, change: Change):
        if change.is_delete() or change.updated.name:
            note_actions.apply_page_change_to_anchor_view(self.state())
