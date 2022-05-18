from misli import Change, logging
from misli.gui.actions_library import action

log = logging.get_logger(__name__)


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

        self.added = {}
        self.update_old_states = {}
        self.update_last_states = {}
        self.removed = {}
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

        There are no sanity checks (e.g. if a removal is made after an update),
        since those are made in the state add/remove/update methods in the
        facade.
        '''
        state_ = change.last_state()

        if change.is_create():
            self.added[state_.id] = state_
            pass

        # On the first update we store the backup (old) state and on it and
        # every subsequent one we store/update the latest state.
        # If an addition and update are made together - an addition with
        # the last state is emitted.
        elif change.is_update():
            if state_.id in self.added:
                self.added[state_.id] = state_
            else:
                if state_.id not in self.update_old_states:
                    self.update_old_states[state_.id] = change.old_state

                self.update_last_states[state_.id] = state_

        # Removals
        else:  # is_delete()
            # If a state is added and deleted - emit nothing
            if state_.id in self.added:
                self.added.pop(state_.id)
                return

            # If a state is updated and then removed - leave just the
            # removal change
            elif state_.id in self.update_old_states:
                self.update_old_states.pop(state_.id)
                self.update_last_states.pop(state_.id)

            self.removed[state_.id] = state_

    def release_aggregated_changes(self, completed_actions):
        changes = []
        for state_id, state_ in self.added.items():
            changes.append(Change.CREATE(state_))

        for state_id, state_ in self.update_old_states.items():
            changes.append(
                Change.UPDATE(state_, self.update_last_states[state_id]))

        for state_id, state_ in self.removed.items():
            changes.append(Change.DELETE(state_))

        self.added.clear()
        self.update_old_states.clear()
        self.update_last_states.clear()
        self.removed.clear()

        if not changes:
            log.info('RELEASE_AGGREGATED_CHANGES: No changes')
            return

        log.info('RELEASE_AGGREGATED_CHANGES:')

        if self.output_channel:
            for change in changes:
                self.output_channel.push(change)

        if self.changeset_output_channel:
            self.changeset_output_channel.push(changes)
