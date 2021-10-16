from typing import Callable

import misli
from .command import Command

log = misli.get_logger(__name__)

_commands = {}


def command(title: str, default_shortcut: str):
    def decorator(function: Callable):
        _command = Command(function, title, default_shortcut)
        _commands[function] = _command
        return _command
    return decorator
