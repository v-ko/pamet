_FIELDS = '__misli_dataclass_fields__'


def get_fields(cls, default=None):
    try:
        attr_name = '__%s_misli_dataclass_fields__' % cls.__name__
        # print('Getting fields at attr_name', attr_name)
        return getattr(cls, attr_name)

    except Exception:
        if default is not None:
            return default

        raise Exception('No dataclass fields attribute. Have you decorated'
                        ' the class with the misli.dataclasses.dataclass?')


def set_fields(cls, fields):
    attr_name = '__%s_misli_dataclass_fields__' % cls.__name__
    # print('Setting fields to %s at attr_name %s' % (fields, attr_name))
    setattr(cls, attr_name, fields)


# Usage: Every subclass should inherit Entity and be decorated by dataclass
# fields with a leading undersocre should have corresponding
# to set a default list, dict or other object - you need to set the field
# to the factory that produces it. That means dataclasses cannot have
# callables (functions) as field values (since they would be assumed to be
# default factories)
def dataclass(cls):
    if 'Entity' not in [c.__name__ for c in cls.__mro__]:
        raise Exception('dataclassses must inherit entity')

    fields = {}
    for c in reversed(cls.__mro__):
        fields.update(get_fields(c, {}))
        # print('Fields from subclass: %s for class %s' % (fields, c.__name__))

    cls_annotations = cls.__dict__.get('__annotations__', {})
    for name, atr_type in cls_annotations.items():
        default = getattr(cls, name, None)

        if name.startswith('_'):
            prop_name = name[1:]
            if type(getattr(cls, prop_name)) != property:
                raise Exception('Misli dataclass fields with a leading '
                                'underscore should have corresponding '
                                ' python properties with the same name '
                                ' without an underscore.')
            fields[prop_name] = default

        else:
            fields[name] = default

    set_fields(cls, fields)
    return cls


@dataclass
class Entity:
    id: str
    obj_type: str = 'Entity'
    obj_class: str = ''

    def __init__(self, **kwargs):
        fields = get_fields(type(self))
        for field_name, default_val in fields.items():
            if callable(default_val):
                def_val = default_val()
            else:
                def_val = default_val

            val = kwargs.pop(field_name, def_val)
            setattr(self, field_name, val)

        if kwargs:
            raise Exception('Unexpected arguments %s' % list(kwargs.keys()))

        self.__post_init__()

    def __post_init__(self):
        pass

    def __copy__(self):
        return self.copy()

    def copy(self):
        return type(self)(**self.state())

    def add_state_keys(self, keys: list):
        fields = get_fields(type(self))
        for key in keys:
            if not hasattr(self, key):
                raise KeyError

            fields[key] = None

        set_fields(type(self), fields)

    # To be deprecated
    def state(self):
        self_dict = {}
        fields = get_fields(type(self))

        for key in fields:
            val = getattr(self, key)

            if type(val) in [list, dict]:
                val = val.copy()

            self_dict[key] = val

        return self_dict

    def asdict(self):
        return self.state()

    # To be deprecated
    def set_state(self, **state):
        fields = get_fields(type(self))
        for key, val in state.items():
            if key not in fields:
                raise KeyError

            setattr(self, key, val)

    def replace(self, **changes):
        self.set_state(**changes)

    def gid(self):
        return self.id
