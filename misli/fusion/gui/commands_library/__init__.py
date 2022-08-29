from typing import Callable, List

import fusion
from .command import Command

log = fusion.get_logger(__name__)

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


def commands() -> List[Command]:
    yield from _commands.values()
