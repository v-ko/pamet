from ast import Dict
from typing import List
from fusion import Change, logging

log = logging.get_logger(__name__)


class AggregatorSlot:
    def __init__(self, first_change):
        self.changes: List[Change] = [first_change]

    def add_change(self, change):
        self.changes.append(change)

    def is_compound(self):
        return len(self.changes) > 1

    def aggregated(self) -> Change:
        if not self.is_compound():
            return self.changes[0]

        added = None
        update_old_state = None
        update_last_state = None
        removed = None
        for change in self.changes:
            last_state = change.last_state()
            if change.is_create():
                if update_last_state or update_old_state:
                    raise Exception('Addition after update')

                if removed:
                    update_old_state = removed
                    removed = None
                    update_last_state = last_state
                else:
                    added = last_state

            # On the first update we store the backup (old) state and on it and
            # every subsequent one we store/update the latest state.
            # If an addition and update are made together - an addition with
            # the last state is emitted.
            elif change.is_update():
                if removed:
                    raise Exception('Update after removal')

                if added:
                    added = last_state
                else:
                    if not update_old_state:
                        update_old_state = change.old_state
                    update_last_state = last_state
            else:  # Change is delete
                if added:
                    removed = added
                    added = None
                elif update_old_state:
                    removed = update_old_state
                    update_old_state = None
                    update_last_state = None
                else:
                    removed = last_state

        if (bool(added) + bool(removed) + bool(update_old_state)) > 1:
            raise Exception

        if added:
            return Change.CREATE(added)
        elif update_last_state:
            if not update_old_state:
                raise Exception
            return Change.UPDATE(update_old_state, update_last_state)
        elif removed:
            return Change.DELETE(removed)


class ChangeAggregator:
    """
    Merges the changes passed to the input_channel and when a message is
    received on the release_trigger_channel - pushes all accumulated changes
    to the output_channel or changeset_output_channel (or both if set).
    The difference between the latter two is that on the changeset channel
    all of the changes are sent as a list as a single message.
    """
    def __init__(
            self,
            input_channel,
            release_trigger_channel,
            output_channel=None,
            changeset_output_channel=None):

        self.slots: Dict[str, AggregatorSlot] = {}
        self.added = {}
        self.update_old_states = {}
        self.update_last_states = {}
        self.removed = {}

        self.create_changes = {}
        self.update_changes = {}
        self.delete_changes = {}

        self.input_channel = input_channel
        self.release_trigger_channel = release_trigger_channel
        self.output_channel = output_channel
        self.changeset_output_channel = changeset_output_channel

        self.raw_sub_id = input_channel.subscribe(
            self.handle_change)
        self.actions_sub_id = release_trigger_channel.subscribe(
            self.release_aggregated_changes)

    def handle_change(self, change: Change):
        '''Parses the recieved changes and reduces them to a single change per
        view state (identified by its id).
        '''
        state = change.last_state()
        if id(state) in self.slots:
            self.slots[id(state)].add_change(change)
        else:
            self.slots[id(state)] = AggregatorSlot(change)

    def release_aggregated_changes(self, completed_actions):
        changes = []
        for slot in self.slots.values():
            changes.append(slot.aggregated())
        self.slots.clear()

        if not changes:
            log.info('RELEASE_AGGREGATED_CHANGES: No changes')
            return

        log.info('RELEASE_AGGREGATED_CHANGES:')

        if self.output_channel:
            for change in changes:
                self.output_channel.push(change)

        if self.changeset_output_channel:
            self.changeset_output_channel.push(changes)
