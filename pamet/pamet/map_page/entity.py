from dataclasses import dataclass

from pamet.entities import Page, register_entity


@register_entity
@dataclass
class MapPage(Page):
    pass
