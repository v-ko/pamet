from typing import List, Union
from fusion import Entity
from fusion.entity_library.change import Change

IMMUTABILITY_ERROR_MESSAGE = (
    'Cannot alter an object after it has been added to the '
    'repo. Make a copy of it and pass it to the repo instead.')


class Repository:

    def insert_one(self, entity: Entity) -> Change:
        entity.set_immutable(error_message=IMMUTABILITY_ERROR_MESSAGE)
        raise NotImplementedError

    def remove_one(self, entity: Entity) -> Change:
        raise NotImplementedError

    def update_one(self, entity: Entity) -> Change:
        entity.set_immutable(error_message=IMMUTABILITY_ERROR_MESSAGE)
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
