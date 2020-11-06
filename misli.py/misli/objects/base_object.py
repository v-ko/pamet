# from misli.objects import State


class BaseObject():
    def __init__(self, **kwargs):
        if 'data' not in kwargs:
            kwargs['data'] = {}
        if 'id' not in kwargs:
            kwargs['id'] = id(self)

        self.__dict__.update(kwargs)

    def state(self):
        return self.__dict__

    # def __del__(self):
