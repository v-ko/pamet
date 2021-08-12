from dataclasses import dataclass

from misli.entity_library import register_entity
from pamet.entities import Page


@register_entity
@dataclass
class MapPage(Page):
    pass
