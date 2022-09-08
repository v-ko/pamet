from __future__ import annotations

from dataclasses import field
from fusion.libs.entity import entity_type, Entity, get_entity_id


@entity_type
class PageChild(Entity):
    id: tuple[str, str] = field(default_factory=lambda: ('', get_entity_id()))

    @property
    def page_id(self):
        return self.id[0]

    @property
    def own_id(self):
        return self.id[1]

    def with_id(self, page_id: str = None, own_id: str = None):
        """A convinience method to produce a copy with a changed id (since
        the 'id' attribute is immutable (used in hashing))."""
        page_id = page_id or self.page_id
        own_id = own_id or self.own_id
        self_dict = self.asdict()
        self_dict['id'] = page_id, own_id
        return type(self)(**self_dict)

    @classmethod
    def in_page(cls,
                page: Page = None,
                page_id: str = None,
                own_id: str = None,
                **child_props):
        if page:
            if page_id:
                raise Exception('Only specify page OR page_id')
            page_id = page.id
        if page_id is None:
            raise Exception('You must specify either page or page_id.')

        own_id = own_id or get_entity_id()
        return cls(id=(page_id, own_id), **child_props)
