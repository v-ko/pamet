"""This module configures the debug options for misli.

Example usage:
    from misli_debug import set_logging , LoggingLevels
    set_logging_level(LoggingLevels.DEBUG)

    import misli
    ...

It's a separate module in order to have a clean syntax for setting the
logging verbosity in test scripts. And the debugging level is set via an
environment variable since logging function decorators are executed upon module
initialization.
"""
import os
from enum import Enum


class LoggingLevels(Enum):
    # Those should be stdlib logging compatible
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0


def set_logging_level(level: LoggingLevels):
    print(f'Setting logging level to {level}')
    os.environ['MISLI_LOGGING_LEVEL'] = level.name
