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
    os.environ['MISLI_LOGGING_LEVEL'] = level.name
