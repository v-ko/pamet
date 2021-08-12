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


def from_dict(self_dict: dict):
    """Construct an entity given its state as a dict"""

    self_id = self_dict.pop('id', '')
    obj_type = self_dict.pop('obj_type')

    cls = get_entity_class_by_name(obj_type)

    instance = cls(**self_dict)
    instance.id = self_id
    instance.obj_type = obj_type
    return instance
