from typing import List, Union
from misli import Entity


class Repository:
    def insert(self, batch: List[Entity]):
        raise NotImplementedError

    def remove(self, batch: List[Entity]):
        raise NotImplementedError

    def update(self, batch: List[Entity]):
        raise NotImplementedError

    def find(self, **filter):
        raise NotImplementedError
