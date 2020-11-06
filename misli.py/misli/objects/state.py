class State():
    def __init__(self, **kwargs):
        # # Default args
        # self.obj_type = kwargs.pop('obj_type')

        self.__dict__ = {}
        self.__dict__.update(kwargs)

    def __contains__(self, key):
        if key in self.__dict__:
            return True

        return False

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, item):
        self.__dict__[key] = item
