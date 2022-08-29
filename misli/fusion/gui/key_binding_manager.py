from typing import List, Union, Any
from collections import defaultdict

import fusion
from fusion import Change
from fusion.gui import Command

log = fusion.get_logger(__name__)

_bindings = set()
_root_views = {}
_bindings_per_command = defaultdict(list)


def condition_string_safety_check(string: str):
    # Remove the allowed operators
    for allowed_operator in ['&', '&&', '|', '||', '!']:
        string.replace(allowed_operator, '')

    # Only identifiers should be left (separated by spaces) - check if they are
    # valid, i.e. are keys in the context dict
    for token in string.split():
        if not token:
            continue

        if token not in fusion.gui.context:
            raise Exception(
                f'The name {token} is not defined in fusion.gui.context')


def process_condition_string(string: str):
    condition_string_safety_check(string)
    code_object = compile(string, '<string>', 'eval')
    return code_object


class KeyBinding:
    def __init__(self,
                 key: str,
                 command: Command,
                 conditions: str = '',
                 view_type: Union[Any, str] = None):
        self._conditions = conditions
        self._condition_code_object = None
        if conditions:
            self._condition_code_object = process_condition_string(conditions)

        self.key = key
        self.command = command

        if isinstance(view_type, str):
            view_type = fusion.gui.view_library.get_view_type(
                class_name=view_type)
        self.view_type = view_type

    def as_tuple(self):
        return (self.key, self.command.name, self._conditions)

    def __hash__(self):
        return hash(self.as_tuple())

    def __eq__(self, other):
        return self.as_tuple() == other.as_tuple()

    @log.traced
    def check_condition_and_invoke_command(self):
        if not self._conditions:
            self.command()
            return

        if eval(self._condition_code_object, {}, fusion.gui.context):
            self.command()
        else:
            log.info(
                f'Skipping command execution for {self.command} conditions '
                f'not met')


def add_key_binding(key_binding):
    if key_binding in _bindings:
        raise Exception('Binding already added')

    _bindings.add(key_binding)
    _bindings_per_command[key_binding.command].append(key_binding)
    for view in fusion.gui.find_views(parent=None):
        fusion.gui.util_provider().add_key_binding(view, key_binding)


def remove_key_binding(key_binding):
    _bindings.remove(key_binding)
    _bindings_per_command[key_binding.command].remove(key_binding)
    for view in fusion.gui.find_views(parent=None):
        fusion.gui.util_provider().remove_key_binding(view, key_binding)


def first_key_binding_for_command(command: Command):
    bindings = _bindings_per_command[command]
    if not bindings:
        return None

    return bindings[0]

def apply_config(key_bindings: List[KeyBinding]):
    if not fusion.gui.util_provider():
        raise Exception('fusion.configure* must be called (so the util provider'
                        ' is set) before you can setup shortcuts')
    new_config = set(key_bindings)
    for_addition = new_config - _bindings
    for_removal = _bindings - new_config

    for binding in for_removal:
        remove_key_binding(binding)

    for binding in for_addition:
        add_key_binding(binding)


def apply_config_from_json(config: List[dict]):
    bindings = []
    for binding_config in config:
        bindings.append(KeyBinding(*binding_config))

    apply_config(bindings)


def handle_root_view_changes(changes: List[Change]):
    for change in changes:
        if change.is_create():
            view = change.last_state().view()
            for binding in _bindings:
                fusion.gui.util_provider().add_key_binding(view, binding)
