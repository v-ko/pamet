class BaseObject():
    def __init__(self, **state):
        self.id = 0
        self.data = {}

        self.__state_keys = state.keys()

        if 'id' not in state:
            state['id'] = id(self)
        if 'data' not in state:
            state['data'] = {}

        self.set_state(**state)

    def state(self):
        self_state = {}
        for k, v in self.__dict__.items():
            if k in self.__state_keys:
                self_state[k] = v

        return self_state

    def set_state(self, **state):
        for k in state:
            if k not in self.__state_keys:
                del state[k]

        self.__dict__.update(state)
