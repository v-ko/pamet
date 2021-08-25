from typing import Union
from datetime import datetime
from dataclasses import dataclass, fields, field

from misli.entity_library import register_entity, get_entity_class_by_name
from misli.helpers import datetime_to_string


@register_entity
@dataclass
class Entity:
    """The base class for entities. Provides several convenience methods for
    conversions to and from dict, copying and attribute updates (via replace())

    All entity subclasses should be decorated with register_entity and
    dataclass (from the dataclasses standard lib) like so:

        from dataclasses import dataclass
        from misli.entity_library import register_entity

        @register_entity
        @dataclass
        class EntitySubclass:
            ...

    Dataclasses provides a nice syntax for attribute declaration (check out
    the python documentation), while the register_entity decorator registers
    the new subclass for the purposes of serialization.

    On construction (in __post_init__) the obj_type attribute gets populated
    with the name of the class. That's relevant for the (de/)serialization.
    The __init__ is used by dataclass, so in order to do stuff upon
    construction you need to reimplement __post_init__ and be sure to call
    the Entity.__post_init__ method in it.
    """

    id: str = field(init=False, default='')
    obj_type: str = field(init=False, default='')

    def __post_init__(self):
        self.obj_type = type(self).__name__

    def gid(self) -> Union[str, tuple]:
        """Returns the global id of the entity. This function can be
        overwritten to return e.g. a tuple of values like
        (self.page_id, self.id)
        """
        return self.id

    def __copy__(self):
        return self.copy()

    def copy(self) -> 'Entity':
        return Entity.from_dict(self.asdict())

    @staticmethod
    def from_dict(self_dict: dict) -> 'Entity':
        """Construct an entity given its state as a dict"""

        self_id = self_dict.pop('id', '')
        obj_type = self_dict.pop('obj_type')

        cls = get_entity_class_by_name(obj_type)
        # Props with a leading underscore in their name have setters/getters and
        # Property methods can't be invoked by the dataclass at init time
        # (it's a long story)
        private_props = {p: self_dict.pop(p) for p in list(self_dict.keys())
                         if p.startswith('_')}

        instance = cls(**self_dict)
        instance.replace(**private_props)
        instance.id = self_id
        instance.obj_type = obj_type
        return instance

    def asdict(self) -> dict:
        """Return the entity properties as a dict"""
        # The dataclasses.asdict recurses and that's not what we want
        self_dict = {f.name: getattr(self, f.name) for f in fields(self)}

        for key, val in self_dict.items():
            if isinstance(val, (list, dict)):
                val = val.copy()
            elif isinstance(val, datetime):
                val = datetime_to_string(val)

            self_dict[key] = val
        return self_dict

    def replace(self, **changes):
        """Update entity properties using keyword arguments"""
        for key, val in changes.items():
            # Apply property changes through the setters
            if key.startswith('_'):
                prop_name = key[1:]
                setattr(self, prop_name, val)

            else:
                setattr(self, key, val)
