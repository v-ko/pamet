from dataclasses import dataclass

from misli import Entity
from misli import get_logger
log = get_logger(__name__)


@dataclass
class Page(Entity):
    name: str = ''
    view_class: str = ''

    def __repr__(self):
        return '<Page id=%s>' % self.id
