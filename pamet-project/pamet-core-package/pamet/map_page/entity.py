from dataclasses import dataclass

from pamet.entities import Page


@dataclass
class MapPage(Page):
    view_class: str = 'MapPage'
