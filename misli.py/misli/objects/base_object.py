# from misli.objects import State


class BaseObject():
    def __init__(self, **kwargs):
        if 'data' not in kwargs:
            kwargs['data'] = {}
        if 'id' not in kwargs:
            kwargs['id'] = id(self)

        self.__dict__.update(kwargs)

        self.__children = []

    def state(self):
        return self.__dict__

    def add_child(self, child):
        self.__children.append(child)

    def get_children(self):
        return self.__children

    # def __del__(self):
