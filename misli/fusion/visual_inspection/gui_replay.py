import os
import json

import fusion
from fusion.gui.actions_library import ACTIONS, ActionCall

log = fusion.get_logger(__name__)


class FusionGuiReplay:
    def __init__(self, actions_meta_path):
        self.last_action_dispatched = None
        self._ended = False
        self.speed = 1

        if not os.path.exists(actions_meta_path):
            raise Exception('Bad path given for the actions recording: "%s"' %
                            actions_meta_path)

        with open(actions_meta_path) as mf:
            action_states = json.load(mf)

        self.actions = [ActionCall(**a) for a in action_states]
        self.actions_left = [ActionCall(**a) for a in action_states]

    def end(self):
        self._ended = True

    def ended(self):
        return self._ended

    def queue_next_action(self, action_states=None):
        if self.ended():
            return

        if not self.actions_left:
            log.info('Reached the end of the recording.')
            self.end()
            return

        action_to_dispatch = self.actions_left[0]
        timeout = action_to_dispatch.start_time

        if self.last_action_dispatched:
            event_action = ActionCall(**action_states[-1])
            # ^^ This event has bad timestamps while replaying

            a0 = self.last_action_dispatched
            a1 = event_action
            if a0.type != a1.type or \
               a0.args != a1.args or \
               a0.kwargs != a1.kwargs:
                raise Exception('Action properties mismatch.')

            timeout -= self.last_action_dispatched.start_time

        actions_count = len(self.actions)
        action_idx = 1 + actions_count - len(self.actions_left)

        log.info('(%s/%s) Dispatching with timeout %s: %s' %
                 (action_idx, actions_count, timeout, action_to_dispatch))
        fusion.call_delayed(
            ACTIONS[action_to_dispatch.type],
            self.speed * timeout,
            action_to_dispatch.args,
            action_to_dispatch.kwargs)

        self.last_action_dispatched = action_to_dispatch
        self.actions_left = self.actions_left[1:]
