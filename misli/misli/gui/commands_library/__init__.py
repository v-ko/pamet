from typing import Callable

import misli
from .command import Command

log = misli.get_logger(__name__)

_commands = {}


def command(title: str, name: str = ''):
    def decorator(function: Callable):
        if not name:
            fname = function.__name__
        else:
            fname = name

        _command = Command(function, title, fname)
        _commands[function] = _command
        return _command
    return decorator
