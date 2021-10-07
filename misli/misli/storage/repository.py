from typing import List, Union
from misli import Entity


class Repository:
    def insert(self, entity_or_batch: Union[Entity, List[Entity]]):
        raise NotImplementedError

    def remove(self, entity_or_batch: Union[Entity, List[Entity]]):
        raise NotImplementedError

    def update(self, entity_or_batch: Union[Entity, List[Entity]]):
        raise NotImplementedError

    def find(self, **filter):
        raise NotImplementedError
