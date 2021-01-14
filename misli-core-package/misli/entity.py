from misli.helpers import get_new_id


class BaseEntity:
    def __init__(self, id: str, obj_type: str, obj_class: str = None):
        self.__state_keys = []

        self.id = id
        self.obj_type = obj_type
        self.obj_class = obj_class

        self.add_state_keys(['id', 'obj_type', 'obj_class'])

    def __copy__(self):
        return self.copy()

    def copy(self):
        return type(self)(**self.state())

    def add_state_keys(self, keys: list):
        for key in keys:
            if not hasattr(self, key):
                raise KeyError

        self.__state_keys.extend(keys)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, new_id: str):
        if not new_id:
            self._id = get_new_id()
            return

        self._id = new_id

    def state(self):
        self_dict = {}
        for key in self.__state_keys:
            val = getattr(self, key)

            if type(val) in [list, dict]:
                val = val.copy()

            self_dict[key] = val

        return self_dict

    def set_state(self, **state):
        for key, val in state.items():
            if key not in self.__state_keys:
                raise KeyError

            setattr(self, key, val)
