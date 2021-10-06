from typing import Any
from dataclasses import dataclass, MISSING, Field

entity_library = {}


@dataclass
class Property:
    name: str
    type: Any = MISSING
    default_value: Any = MISSING
    property_object: property = None


def _apply_dataclass_and_process_properties(entity_class):
    marked_props = [
        ann for ann in entity_class.__annotations__ if ann.startswith('_')
    ]
    processed_props = []

    for prop_name in marked_props:
        prop_type = entity_class.__annotations__.pop(prop_name)
        default_val = getattr(entity_class, prop_name, MISSING)

        # Delete the underscored attribute
        delattr(entity_class, prop_name)

        # Get the property object (produced by @property)
        prop_name_stripped = prop_name[1:]  # Remove the underscore
        prop_obj = getattr(entity_class, prop_name_stripped, None)

        # Remove the property object, because we need to apply the dataclass
        # decorator without it present. The attribute with that name is used
        # by the dataclass library to define the default value (or declare
        # the field())
        delattr(entity_class, prop_name_stripped)

        processed_props.append(
            Property(prop_name_stripped, prop_type, default_val, prop_obj))

    # Re-add the annotation (name,type) information and attribute with default
    # value but for the stripped name.
    for prop in processed_props:
        if prop.name in entity_class.__annotations__:
            raise Exception(
                f'An attribute "{prop.name}" already exists. Can not convert'
                f'"_{prop.name}". Mind that misli processess dataclass fields'
                f' with a leading underscore in the name to merge them with '
                f'the respective property methods. Check the docs/code for'
                f' more information.')

        entity_class.__annotations__[prop.name] = prop.type
        if prop.default_value is not MISSING:
            setattr(entity_class, prop.name, prop.default_value)

    # Apply the dataclass decorator manually
    entity_class = dataclass(entity_class)

    for prop in processed_props:
        # Replace the property attributes with the property objects
        if prop.property_object:
            setattr(entity_class, prop.name, prop.property_object)

        # Set the default value to the private var (with leading underscore)
        # if one has been specified (as it might be used by the property methods)
        if prop.default_value is not MISSING:
            # If the attribute is defined with dataclass.field() - get the
            # default value from there
            if isinstance(prop.default_value, Field):
                default_val = prop.default_value.default
            else:
                default_val = prop.default_value

            setattr(entity_class, '_' + prop.name, default_val)

    return entity_class


def wrap_and_register_entity_type(entity_class: Any):
    """A class decorator to register entities in the entity library for the
    purposes of serialization and deserialization. It applies the dataclass
    decorator.

    It also allows using computed properties with dataclasses. Declare the
    property with a leading underscore in the name. Declare the @property style
    methods with the same name (without an underscore) and the dataclass will
    use them. This is something the dataclasses lib does not handle by default.
    For example:

    @register_entity_type
    class Vehicle(Entity):
        _wheels: int = 5

        @property
        def wheels(self):
            return self._wheels

        @wheels.setter
        def wheels(self, num_wheels):
            self._wheels = num_wheels // 2 * 2  # Reduce to an even number

    Raises:
        Exception: on duplicate registration
    """
    entity_class = _apply_dataclass_and_process_properties(entity_class)

    # Register the entity class
    entity_class_name = entity_class.__name__
    if entity_class_name in entity_library:
        raise Exception('This entity class name is already registered: %s' %
                        entity_class_name)

    entity_library[entity_class_name] = entity_class
    return entity_class


def get_entity_class_by_name(entity_class_name: str):
    return entity_library[entity_class_name]


def from_dict(self_dict: dict) -> 'Entity':
    """Construct an entity given its state as a dict"""
    type_name = self_dict.pop('type_name')
    cls = get_entity_class_by_name(type_name)

    instance = cls(**self_dict)
    return instance
