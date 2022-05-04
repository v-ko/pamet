from misli import Change, logging
from misli.gui import channels

log = logging.get_logger(__name__)


class StateAggregator:
    def __init__(self, input_channel, output_channel):
        self.added = {}
        self.update_old_states = {}
        self.update_last_states = {}
        self.removed = {}

        self.raw_sub_id = input_channel.subscribe(
            self.handle_state_changes)
        self.actions_sub_id = output_channel.subscribe(
            self.release_aggregated_changes)

    def handle_state_changes(self, change: Change):
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
        for state_id, state_ in self.added.items():
            channels.state_changes_by_id.push(Change.CREATE(state_))

        for state_id, state_ in self.update_old_states.items():
            channels.state_changes_by_id.push(
                Change.UPDATE(state_, self.update_last_states[state_id]))

        for state_id, state_ in self.removed.items():
            channels.state_changes_by_id.push(Change.DELETE(state_))

        self.added.clear()
        self.update_old_states.clear()
        self.update_last_states.clear()
        self.removed.clear()
