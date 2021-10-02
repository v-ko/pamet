from misli import Entity, register_entity_type
from misli import get_logger
log = get_logger(__name__)


@register_entity_type
class Page(Entity):
    name: str = ''

    def __repr__(self):
        return '<Page id=%s>' % self.id
