from misli import misli
from misli.objects.base_object import BaseObject


class Component(BaseObject):
    def __init__(self, parent_id, obj_class):
        BaseObject.__init__(
            self,
            obj_type='Component',
            obj_class=obj_class)

        self.parent_id = parent_id
        self.__children = []

    def set_props(self, **props):
        pass

    def add_child(self, child_id):
        child = misli.component(child_id)
        self.__children.append(child)

    def remove_child(self, child_id):
        child = misli.component(child_id)
        if child not in self.__children:
            return

        self.__children.remove(child)

    def get_children(self):
        return self.__children
