from misli.entities import BaseEntity
from misli import get_logger
log = get_logger(__name__)


class Page(BaseEntity):
    def __init__(self, **page_state):
        id = page_state.pop('id', None)
        obj_class = page_state.pop('obj_class', None)

        BaseEntity.__init__(
            self, id=id, obj_type='Page', obj_class=obj_class)

        self.name = page_state.get('name', '')
        self.add_state_keys(['name'])

    def __repr__(self):
        return '<Page id=%s>' % self.id
