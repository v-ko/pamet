from __future__ import annotations

from fusion.libs.model import Entity, entity_type, get_entity_id


@entity_type
class PageChild(Entity):
    """Base for page-scoped entities (notes, arrows).

    ID is a flat opaque string (matching TS PametElement).
    parent_id holds the page ID (inherited from Entity).
    """

    @property
    def page_id(self) -> str:
        return self.parent_id

    @classmethod
    def create(cls, page_id: str, **child_props):
        """Create a PageChild with a flat ID and parent_id set to page_id."""
        return cls(id=get_entity_id(), parent_id=page_id, **child_props)
