from collections import defaultdict

from misli import log
# from misli.helpers import new_int_id


class Subscription():
    def __init__(self, callback, slice_id):
        self.callback = callback
        self.slice_id = slice_id


class StateManager():
    def __init__(self):
        self.states = {}  # By _id
        self.subscriptions = defaultdict(list)

    def load(self, state):
        self.states[state._id] = state

    def unload(self, state):
        if state._id in self.states:
            del self.states[state._id]
        else:
            log.error('[StateManager] unload called for missing id', state)
        return state

    def subscribe(self, slice_id, callback):
        subscription = Subscription(callback)
        self.subscriptions[slice_id].append(subscription)

        return id(subscription)

    def unsubscribe(self, subscription_id):
        for slice_id, sub_list in self.subscriptions:
            for sub in sub_list:
                if id(sub) != subscription_id:
                    continue
                del sub_list[sub_list.index(sub)]
                return True

        return False

    def update(self, new_state):
        state = self.states[new_state._id]
        old_state = state.copy()

        state.update(new_state)

        if state == old_state:
            return

        # Notify subscribers
        if state._id in self.subscriptions:
            for sub in self.subscriptions:
                sub.callback(old_state, new_state)

    def find(self, **kwargs):
        for state in self.states:
            skip = False
            for key, value in kwargs.items():
                if key not in state:
                    skip = True
                    continue

                if state[key] != value:
                    skip = True

            if not skip:
                yield state
