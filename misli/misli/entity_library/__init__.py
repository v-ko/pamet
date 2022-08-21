from __future__ import annotations
from typing import Any
from dataclasses import dataclass, MISSING, Field

from misli.logging import get_logger

log = get_logger(__name__)
entity_library = {}


@dataclass
class Property:
    name: str
    type: Any = MISSING
    default_value: Any = MISSING
    property_object: property = None


def __hash__(self):
    return hash(self.gid())


def __eq__(self, other: Entity) -> bool:
    if not other:
        return False
    return self.gid() == other.gid()


def __setattr__(self, key, value):
    if self.immutability_error_message:
        raise Exception(self.immutability_error_message)

    field_names = [f.name for f in fields(self)]
    if not hasattr(self, key) and key not in field_names:
        raise Exception('Cannot set missing attribute')

    # Since ids are used for hashing - it's wise to make them immutable
    if key == 'id' and hasattr(self, 'id'):
        raise Exception

    object.__setattr__(self, key, value)


def entity_type(entity_class: Any, repr: bool = False):
    """A class decorator to register entities in the entity library for the
    purposes of serialization and deserialization. It applies the dataclass
    decorator.
    """
    # entity_class = _apply_dataclass_and_process_properties(entity_class)

    # Transplant __hash__ and __eq__ into every entity upon registration
    # because the dataclasses lib disregards the inherited ones
    entity_class.__hash__ = __hash__
    entity_class.__eq__ = __eq__

    entity_class = dataclass(entity_class, repr=repr)

    # Register the entity class
    entity_class_name = entity_class.__name__
    if entity_class_name in entity_library:
        raise Exception('This entity class name is already registered: %s' %
                        entity_class_name)

    entity_library[entity_class_name] = entity_class
    return entity_class


def get_entity_class_by_name(entity_class_name: str):
    return entity_library[entity_class_name]


def from_dict(type_name: str, entity_dict: dict) -> Entity:
    """Construct an entity given its state as a dict"""
    cls = get_entity_class_by_name(type_name)
    if 'id' in entity_dict:
        instance = cls(id=entity_dict.pop('id'))
    else:
        instance = cls()

    leftovers = instance.replace_silent(**entity_dict)
    if leftovers:
        log.error(f'Leftovers while loading entity '
                  f'(id={entity_dict.get("id", None)}): {leftovers}')
    return instance
