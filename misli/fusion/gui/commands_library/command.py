from typing import Callable
from fusion import get_logger

log = get_logger(__name__)


class Command:
    def __init__(self,
                 function: Callable,
                 title: str,
                 name: str):
        self.function = function
        self.title = title
        self.name = name

    def __repr__(self):
        return f'<Command title={self.title}>'

    def __call__(self, **context):
        log.info(f'COMMAND triggered: {self}')
        return self.function(**context)
