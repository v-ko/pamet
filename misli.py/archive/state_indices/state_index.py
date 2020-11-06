from collections import defaultdict


class StateIndex():
    def __init__(self, indexed_field, filter_dict):
        self.states = defaultdict(list)
        self.state_manager = None
        self.filter_dict = filter_dict

    def __getitem__(self, key):
        pass

    def connect_to(self, state_manager):
        state_manager.subscribe(self.filter, self.handle_update)

    def handle_update(self, state_before, state_after):
        # Check if indexed field in state keys
        # Check if removed properly

        index_row = self.states[state_after[self.indexed_field]]

        if not state_before:  # Create
            index_row.append(state_after)
            return True

        if not state_after:  # Delete
            index_row.remove(state_before)
            return True

        state_idx = index_row.index(state_before)
        index_row[state_idx].update(state_after)
