from collections import defaultdict
from typing import Any, Generator, List
from misli.entity_library.change import Change
from misli.entity_library.entity import Entity
from misli.helpers import find_many_by_props
from misli.storage.repository import Repository


class InMemoryRepository(Repository):

    def __init__(self):
        super().__init__()
        self._entity_cache = {}
        self._entity_cache_by_parent = defaultdict(set)

    def upsert_to_cache(self, entity: Entity):
        self._entity_cache[entity.gid()] = entity
        if entity.parent_gid():
            self._entity_cache_by_parent[entity.parent_gid()].add(entity.gid())

    def insert_one(self, entity: Entity) -> Change:
        if entity.gid() in self._entity_cache:
            raise Exception(
                'Cannot insert {entity}, since it already exists')

        self.upsert_to_cache(entity)
        return Change.CREATE(entity)

    def insert(self, batch: List[Entity]):
        return [self.insert_one(entity) for entity in batch]

    def remove_one(self, entity: Entity) -> Change:
        old_entity = self._entity_cache.pop(entity.gid(), None)
        if not old_entity:
            raise Exception(f'Cannot remove missing {entity}')

        if old_entity.parent_gid():
            self._entity_cache_by_parent[old_entity.parent_gid()].remove(
                old_entity.gid())

        return Change.DELETE(old_entity)

    def remove(self, batch: List[Entity]):
        return [self.remove_one(entity) for entity in batch]

    def update_one(self, entity: Entity) -> Change:
        old_entity = self._entity_cache.pop(entity.gid(), None)
        if not old_entity:
            raise Exception('Cannot update missing {entity}')

        self.upsert_to_cache(entity)
        return Change.UPDATE(old_entity, entity)

    def update(self, batch: List[Entity]):
        return [self.update_one(entity) for entity in batch]

    def find_cached(self, **filter):
        # If searching by gid - there will be only one unique result (if any)
        if 'gid' in filter:
            gid = filter.get('gid')
            try:
                result = self._entity_cache.get(gid, None)
            except TypeError:
                result = []
            yield from [result] if result else []

        # If searching by parent_gid - use the index to do it efficiently
        if 'parent_gid' in filter:
            parent_gid = filter.pop('parent_gid')
            try:
                found = self._entity_cache_by_parent.get(parent_gid, [])
            except TypeError:
                found = []
            search_set = (self._entity_cache[gid] for gid in found)
        else:
            search_set = self._entity_cache.values()

        # Searching by type_name is a special case
        if 'type_name' in filter:
            type_name = filter.pop('type_name')
            search_set = (
                ent for ent in search_set
                if type(ent).__name__ == type_name
            )
        if filter:
            search_set = find_many_by_props(search_set, **filter)
        yield from search_set

    def find(self, **filter) -> Generator[Any, None, None]:
        yield from (entity.copy() for entity in self.find_cached(**filter))
