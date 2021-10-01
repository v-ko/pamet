from typing import Any
from dataclasses import dataclass

entity_library = {}


def register_entity(entity_class: Any):
    """A class decorator to register entities in the entity library for the
    purposes of serialization and deserialization.

    Raises:
        Exception: on duplicate registration
    """
    # Apply the dataclass decorator manually
    entity_class = dataclass(entity_class)

    entity_class_name = entity_class.__name__

    if entity_class_name in entity_library:
        raise Exception('This entity class name is already registered: %s' %
                        entity_class_name)

    entity_library[entity_class_name] = entity_class
    return entity_class


def get_entity_class_by_name(entity_class_name: str):
    return entity_library[entity_class_name]
