from __future__ import annotations

from dataclasses import field
from misli.entity_library import entity_type
from misli.entity_library.entity import Entity

from misli.helpers import get_new_id


@entity_type
class PageChild(Entity):
    id: tuple[str, str] = field(default_factory=lambda: ('', get_new_id()))

    @property
    def page_id(self):
        return self.id[0]

    @property
    def own_id(self):
        return self.id[1]

    def with_id(self, page_id: str = None, own_id: str = None):
        """A convinience method to produce a copy with a changed id (since
        the 'id' attribute is immutable (used in hashing))."""
        page_id = page_id or get_new_id()
        own_id = own_id or get_new_id()
        self_dict = self.asdict()
        self_dict['id'] = page_id, own_id
        return type(self)(**self_dict)

    @classmethod
    def in_page(cls, page: Page, own_id: str = None, **child_props):
        own_id = own_id or get_new_id()
        return cls(id=(page.id, own_id), **child_props)
