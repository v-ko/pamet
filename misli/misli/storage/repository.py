from typing import List, Union
from misli import Entity
from misli.entity_library.change import Change


class Repository:
    def insert_one(self, entity: Entity) -> Change:
        raise NotImplementedError

    def remove_one(self, entity: Entity) -> Change:
        raise NotImplementedError

    def update_one(self, entity: Entity) -> Change:
        raise NotImplementedError

    def insert(self, batch: List[Entity]):
        raise NotImplementedError

    def remove(self, batch: List[Entity]):
        raise NotImplementedError

    def update(self, batch: List[Entity]):
        raise NotImplementedError

    def find(self, **filter) -> Entity:
        raise NotImplementedError

    def find_one(self, **filter) -> List[Entity]:
        found = self.find(**filter)

        for f in found:
            return f

        return None
