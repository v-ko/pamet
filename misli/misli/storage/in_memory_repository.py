from collections import defaultdict
from typing import Any, Generator, List
from misli.entity_library.change import Change
from misli.entity_library.entity import Entity
from misli.helpers import find_many_by_props
from misli.storage.repository import IMMUTABILITY_ERROR_MESSAGE, Repository


class InMemoryRepository(Repository):

    def __init__(self, types_for_cached_type_filtering: tuple = None):
        super().__init__()
        self.types_for_cached_type_filtering = types_for_cached_type_filtering

        self._entity_cache = {}
        self._entity_cache_by_parent = defaultdict(set)
        self._entity_cache_by_type = defaultdict(set)

    def type_cache_supported_subclass(self, entity: Entity):
        for supported_class in self.types_for_cached_type_filtering:
            if isinstance(entity, supported_class):
                return supported_class

    def upsert_to_cache(self, entity: Entity) -> Entity | None:
        """Adds an entity to the cache. Returns the old entity or None"""
        old_entity = self.pop_from_cache(entity.gid())

        # Make the entity immutable (works only in debug mode!)
        entity.set_immutable(error_message=IMMUTABILITY_ERROR_MESSAGE)

        # Insert it into the indices
        self._entity_cache[entity.gid()] = entity

        if self.types_for_cached_type_filtering:
            supported_subclass = self.type_cache_supported_subclass(entity)
            if supported_subclass:
                self._entity_cache_by_type[supported_subclass].add(entity)
        if entity.parent_gid():
            self._entity_cache_by_parent[entity.parent_gid()].add(entity)
        return old_entity

    def pop_from_cache(self, entity_gid: str | tuple) -> Entity:
        entity = self._entity_cache.pop(entity_gid, None)
        if not entity:
            return None

        if self.types_for_cached_type_filtering:
            supported_subclass = self.type_cache_supported_subclass(entity)
            if supported_subclass:
                self._entity_cache_by_type[supported_subclass].remove(entity)

        if entity.parent_gid():
            self._entity_cache_by_parent[entity.parent_gid()].remove(entity)

        return entity

    def insert_one(self, entity: Entity) -> Change:
        if entity.gid() in self._entity_cache:
            raise Exception('Cannot insert {entity}, since it already exists')

        self.upsert_to_cache(entity)
        return Change.CREATE(entity)

    def update_one(self, entity: Entity) -> Change:
        old_entity = self.pop_from_cache(entity.gid())
        if not old_entity:
            raise Exception('Cannot update missing {entity}')

        self.upsert_to_cache(entity)
        return Change.UPDATE(old_entity, entity)

    def remove_one(self, entity: Entity) -> Change:
        old_entity = self.pop_from_cache(entity.gid())
        if not old_entity:
            raise Exception(f'Cannot remove missing {entity}')

        return Change.DELETE(old_entity)

    def insert(self, batch: List[Entity]):
        return [self.insert_one(entity) for entity in batch]

    def remove(self, batch: List[Entity]):
        return [self.remove_one(entity) for entity in batch]

    def update(self, batch: List[Entity]):
        return [self.update_one(entity) for entity in batch]

    def find_cached(self,
                    gid: str | tuple = None,
                    type: Any = None,
                    parent_gid: str | tuple = None,
                    **filter) -> Generator[Any, None, None]:
        # If searching by gid - there will be only one unique result (if any)
        if gid:
            try:
                result = self._entity_cache.get(gid, None)
            except TypeError:
                result = []
            if result:
                yield result
                return
            else:
                return

        # If searching by parent_gid - use the index to do it efficiently
        if parent_gid:
            try:
                search_set = self._entity_cache_by_parent.get(
                    parent_gid, set())
            except TypeError:
                search_set = []
        else:
            search_set = set(self._entity_cache.values())

        # Searching by type_name is a special case
        if type:
            if self.types_for_cached_type_filtering and \
                    type in self.types_for_cached_type_filtering:
                type_search_set = self._entity_cache_by_type.get(type, set())
                search_set = search_set.intersection(type_search_set)
            else:
                search_set = (e for e in search_set if isinstance(e, type))

        # Apply the rest of the filter
        if filter:
            search_set = find_many_by_props(search_set, **filter)
        yield from search_set

    def find(self,
             gid: str | tuple = None,
             type: Any = None,
             parent_gid: str | tuple = None,
             **filter) -> Generator[Any, None, None]:
        yield from (entity.copy() for entity in self.find_cached(
            gid, type, parent_gid, **filter))
