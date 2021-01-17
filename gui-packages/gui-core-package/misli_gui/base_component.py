from __future__ import annotations
from misli.dataclasses import Entity, dataclass
from misli import get_logger
log = get_logger(__name__)


@dataclass
class Component(Entity):
    def __init__(self, parent_id: str, obj_class: str):
        Entity.__init__(
            self, id='', obj_type='Component', obj_class=obj_class)

        self.parent_id = parent_id
        self.add_state_keys(['parent_id'])

        self.__children = {}

        self.pcommand_cache = None
        self.image_cache = None

        self.should_rebuild_pcommand_cache = True
        self.should_reallocate_image_cache = True
        self.should_rerender_image_cache = True

    @log.traced
    def set_props_from_entity(self, **entity_props):
        pass

    @log.traced
    def add_child(self, child: Component):
        self.__children[child.id] = child

    @log.traced
    def remove_child(self, child: Component):
        if child.id not in self.__children:
            return

        del self.__children[child.id]

    def child(self, child_id: str):
        return self.__children[child_id]

    def get_children(self):
        return [c for cid, c in self.__children.items()]

    @log.traced
    def update(self):
        raise NotImplementedError
