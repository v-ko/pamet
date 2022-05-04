from typing import Union
from datetime import datetime
from dataclasses import fields, field, replace

from misli import entity_library
from misli.helpers import datetime_to_string, get_new_id


@entity_library.entity_type
class Entity:
    """The base class for entities. Provides several convenience methods for
    conversions to and from dict, copying and attribute updates (via replace())

    All entity subclasses should be decorated with register_entity_type like so:

        from misli.entity_library import register_entity_type

        @register_entity_type
        class EntitySubclass:
            ...

    Dataclasses provides a nice syntax for attribute declaration (check out
    the python documentation), while the register_entity_type decorator
    registers the new subclass for the purposes of serialization.

    The __init__ is used by dataclass, so in order to do stuff upon
    construction you need to reimplement __post_init__.

    If you want to use computed properties declared via @property you should
    declare the dataclass attributes with a leading underscore and the methods
    without it. See the register_entity_type docs for an example.
    """

    id: str = field(default_factory=get_new_id)

    def __eq__(self, other: 'Entity') -> bool:
        if not other:
            return False
        return self.id == other.id
        # return self.asdict() == other.asdict()

    def __copy__(self):
        return self.copy()

    def copy(self) -> 'Entity':
        return replace(self, **self.asdict())

    def gid(self) -> Union[str, tuple]:
        """Returns the global id of the entity. This function can be
        overwritten to return e.g. a tuple of values like
        (self.page_id, self.id)
        """
        return self.id

    def asdict(self) -> dict:
        """Return the entity properties as a dict"""
        # The dataclasses.asdict recurses and that's not what we want
        self_dict = {f.name: getattr(self, f.name) for f in fields(self)}

        for key, val in self_dict.items():
            if isinstance(val, (list, dict)):
                val = val.copy()
                self_dict[key] = val
            elif isinstance(val, datetime):
                val = datetime_to_string(val)
                self_dict[key] = val

        # self_dict['type_name'] = type(self).__name__

        return self_dict

    def replace(self, **changes):
        """Update entity properties using keyword arguments"""
        for key, val in changes.items():
            setattr(self, key, val)

    def parent_gid(self):
        """Implement this to return the parent global id
        """
        return None
