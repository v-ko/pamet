from misli import Entity, register_entity_type
from misli import get_logger
import pamet

log = get_logger(__name__)


@register_entity_type
class Page(Entity):
    name: str = ''

    def __repr__(self):
        return '<Page id=%s>' % self.id

    def notes(self):
        return pamet.notes(self.gid())