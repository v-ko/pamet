entity_library = {}


def register_entity(entity_class):
    """A class decorator to register entities in the entity library for the
    purposes of serialization and deserialization.

    Raises:
        Exception: on duplicate registration
    """
    entity_class_name = entity_class.__name__

    if entity_class_name in entity_library:
        raise Exception('This entity class name is already registered: %s' %
                        entity_class_name)

    entity_library[entity_class_name] = entity_class
    return entity_class


def get_entity_class_by_name(entity_class_name):
    return entity_library[entity_class_name]
