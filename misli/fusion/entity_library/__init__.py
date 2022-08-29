from __future__ import annotations
import json
from typing import Any
from dataclasses import dataclass, MISSING

from fusion.logging import get_logger

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

    if hasattr(entity_class, 'type_name'):
        raise Exception('The type_name identifier is used in the '
                        'serialization and is prohibited.')

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


def dump_to_dict(entity: Entity) -> dict:
    entity_dict = entity.asdict()

    if 'type_name' in entity_dict:
        raise Exception

    type_name = type(entity).__name__
    entity_dict['type_name'] = type_name
    return entity_dict


def dump_as_json(entity: Entity, ensure_ascii=False, **dump_kwargs):
    entity_dict = dump_to_dict(entity)
    json_str = json.dumps(entity_dict, ensure_ascii=False, **dump_kwargs)
    return json_str


def load_from_json(json_str: str):
    raise Exception('not tested')
    entity_dict = json.loads(json_str)
    load_from_dict(entity_dict)


def load_from_dict(entity_dict: dict):
    type_name = entity_dict.pop('type_name')
    cls = get_entity_class_by_name(type_name)

    if 'id' in entity_dict:
        id = entity_dict.pop('id')
        if isinstance(id, list):  # Mostly when deserializing
            id = tuple(id)
        instance = cls(id=id)
    else:
        instance = cls()

    leftovers = instance.replace_silent(**entity_dict)
    if leftovers:
        log.error(f'Leftovers while loading entity '
                  f'(id={entity_dict.get("id", None)}): {leftovers}')
    return instance
