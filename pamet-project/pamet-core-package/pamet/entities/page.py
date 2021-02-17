from misli.dataclasses import Entity, dataclass
from misli import get_logger
log = get_logger(__name__)


@dataclass
class Page(Entity):
    name: str = ''

    def __post_init__(self, **page_state):
        self.obj_type = 'Page'

    def __repr__(self):
        return '<Page id=%s>' % self.id
