from dataclasses import dataclass, fields, field


@dataclass
class Entity:
    id: str = field(init=False, default='')
    obj_type: str = field(init=False, default='')

    @classmethod
    def from_dict(cls, self_dict: dict):
        self_id = self_dict.pop('id', '')
        obj_type = self_dict.pop('obj_type', '')

        instance = cls(**self_dict)
        instance.id = self_id
        instance.obj_type = obj_type
        return instance

    def __post_init__(self):
        self.obj_type = type(self).__name__

    def __copy__(self):
        return self.copy()

    def copy(self):
        self_class = type(self)
        return self_class.from_dict(self.asdict())

    def asdict(self):
        # The dataclasses.asdict recurses and that's not what we want
        self_dict = {f.name: getattr(self, f.name) for f in fields(self)}

        for key, val in self_dict.items():
            if type(val) in [list, dict]:
                val = val.copy()

            self_dict[key] = val
        return self_dict

    def replace(self, **changes):
        for key, val in changes.items():
            # Apply property changes through the setters
            if key.startswith('_'):
                prop_name = key[1:]
                setattr(self, prop_name, val)

            else:
                setattr(self, key, val)

    def gid(self):
        return self.id
