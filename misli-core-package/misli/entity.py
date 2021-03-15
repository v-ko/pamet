from dataclasses import dataclass, fields


@dataclass
class Entity:
    id: str = ''
    obj_type: str = ''

    def __post_init__(self):
        self.obj_type = type(self).__name__

    def __copy__(self):
        return self.copy()

    def copy(self):
        self_class = type(self)
        self_dict = self.asdict()

        return self_class(**self_dict)

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
