from typing import Callable
from misli import get_logger

log = get_logger(__name__)


class Command:
    def __init__(self,
                 function: Callable,
                 title: str,
                 shortcut: str = None,
                 context: dict = None):
        self.function = function
        self.title = title
        self.shortcut = shortcut
        self.context = context or {}

    def __repr__(self):
        return f'<Command title={self.title}>'

    def __call__(self, **context):
        log.info(f'COMMAND triggered: {self}')
        if not context:
            context = self.context
        return self.function(**context)
