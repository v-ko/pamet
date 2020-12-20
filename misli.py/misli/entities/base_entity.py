class BaseEntity:
    def __init__(self, id, obj_type, obj_class=None):
        self.__state_keys = []

        self.id = id
        self.obj_type = obj_type
        self.obj_class = obj_class

        self.add_state_keys(['id', 'obj_type', 'obj_class'])

    def add_state_keys(self, keys):
        if type(keys) != list:
            raise ValueError

        self.__state_keys.extend(keys)

    def state(self):
        self_state = {}
        for k, v in self.__dict__.items():
            if k in self.__state_keys:
                self_state[k] = v

        return self_state

    def set_state(self, **state):
        filtered = {k: state[k] for k in state if k in self.__state_keys}

        self.__dict__.update(filtered)
