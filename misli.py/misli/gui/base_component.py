from misli.entities.base_entity import BaseEntity


class Component(BaseEntity):
    def __init__(self, parent_id, obj_class):
        BaseEntity.__init__(
            self, id=None, obj_type='Component', obj_class=obj_class)

        self.parent_id = parent_id
        self.add_state_keys(['parent_id'])

        self.__children = {}

        self.pcommand_cache = None
        self.image_cache = None

        self.should_rebuild_pcommand_cache = True
        self.should_reallocate_image_cache = True
        self.shoud_rerender_image_cache = True

    def set_props_from_base_object(self, **base_object_props):
        pass

    def add_child(self, child):
        self.__children[child.id] = child

    def remove_child(self, child):
        if child.id not in self.__children:
            return

        del self.__children[child.id]

    def child(self, child_id):
        return self.__children[child_id]

    def get_children(self):
        return [c for cid, c in self.__children.items()]

    def update(self):
        raise NotImplementedError
