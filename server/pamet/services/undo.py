from collections import defaultdict
from typing import Dict, List
from fusion.libs.channel import Channel
from fusion.libs.entity.change import Change
import pamet
from pamet.model.page import Page
from pamet.model.page_child import PageChild

MAX_UNDO_HISTORY_SIZE = 1000


class UndoHistory:

    def __init__(self) -> None:
        self._history: List[Change] = []
        self._position_in_history = 0  # 0 is before any changes
        self.applied_changes = []

    def handle_change_set(self, change_set: List[Change]):
        # Filter out the changes that were made by this service
        regular_changes = []
        undo_changes = []
        for change in change_set:
            if change in self.applied_changes:
                undo_changes.append(change)
                self.applied_changes.remove(change)
            else:
                regular_changes.append(change)

        # Undo changes are expected to be in bulk and any leftovers are a
        # sign of a problem
        if undo_changes and (regular_changes or self.applied_changes):
            raise Exception

        if not regular_changes:
            return

        if (self._history and self._position_in_history <
            (len(self._history) - 1)):
            self._history = self._history[:self._position_in_history + 1]
        self._history.append(regular_changes)

        # Keep the hitory size in check
        if len(self._history) > MAX_UNDO_HISTORY_SIZE:
            self._history.pop(0)

        self._position_in_history = len(self._history)

    def has_undo_back(self):
        return self._position_in_history > 0

    def has_undo_forward(self):
        return self._position_in_history < len(self._history)

    def back_one_step(self):
        if not self._history:
            return

        # Index is at the beginning (before changes)
        if not self.has_undo_back():
            return

        changes_to_revert = self._history[self._position_in_history - 1]
        for change in changes_to_revert:
            reversed_change = change.reversed()
            pamet.apply_change(reversed_change)
            self.applied_changes.append(reversed_change)

        self._position_in_history -= 1

    def forward_one_step(self):
        if not self._history:
            return

        # Index is at the end
        if not self.has_undo_forward():
            return

        changes_to_revert = self._history[self._position_in_history]
        for change in changes_to_revert:
            pamet.apply_change(change)
            self.applied_changes.append(change)

        self._position_in_history += 1


class UndoService:

    def __init__(self, change_sets_channel: Channel):
        self._histories_by_page_id: Dict[str, UndoHistory] = defaultdict(
            UndoHistory)

        self.change_channel = change_sets_channel
        change_sets_channel.subscribe(self.handle_change_set)

    def handle_change_set(self, change_set: List[Change]):
        # Validate the change set and determine the page
        changes_by_page_id = defaultdict(list)
        for change in change_set:
            state = change.last_state()
            if isinstance(state, PageChild):
                changes_by_page_id[state.page_id].append(change)
            elif isinstance(state, Page):
                changes_by_page_id[state.id].append(change)
            else:
                raise Exception

        for page_id, changeset_for_page in changes_by_page_id.items():
            self._histories_by_page_id[page_id].handle_change_set(
                changeset_for_page)

    def has_undo_forward(self, page_id):
        if page_id not in self._histories_by_page_id:
            return False
        else:
            return self._histories_by_page_id[page_id].has_undo_forward()

    def has_undo_back(self, page_id):
        if page_id not in self._histories_by_page_id:
            return False
        else:
            return self._histories_by_page_id[page_id].has_undo_back()

    def back_one_step(self, page_id):
        if page_id not in self._histories_by_page_id:
            return
        self._histories_by_page_id[page_id].back_one_step()

    def forward_one_step(self, page_id):
        if page_id not in self._histories_by_page_id:
            return
        self._histories_by_page_id[page_id].forward_one_step()
