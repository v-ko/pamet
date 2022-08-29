from __future__ import annotations

from typing import Union
from fusion.basic_classes.point2d import Point2D
from fusion.logging import get_logger
import pamet
from pamet.constants import ALIGNMENT_GRID_UNIT
from pamet.model.page import Page

log = get_logger(__name__)


def snap_to_grid(x: Union[float, Point2D]) -> Union[float, Point2D]:
    return round(x / ALIGNMENT_GRID_UNIT) * ALIGNMENT_GRID_UNIT


def generate_page_name() -> str:
    base_name = 'New page'  # Could be replaced with config, translations, etc.

    page_name = base_name
    default_names_found = 0
    while True:
        if not pamet.find_one(name=page_name, type=Page):
            return page_name
        default_names_found += 1
        page_name = f'{base_name} {default_names_found}'


def get_default_page():
    config = pamet.desktop_app.get_config()
    return pamet.page(config.home_page_id)


