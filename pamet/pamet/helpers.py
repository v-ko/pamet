from typing import List, Union
from misli.basic_classes.point2d import Point2D
import pamet
from pamet.constants import ALIGNMENT_GRID_UNIT
# from pamet.desktop_app.config import get_config


def snap_to_grid(x: Union[float, Point2D]) -> Union[float, Point2D]:
    return round(x / ALIGNMENT_GRID_UNIT) * ALIGNMENT_GRID_UNIT


def generate_page_name() -> str:
    base_name = 'New page'  # Could be replaced with config, translations, etc.

    page_name = base_name
    default_names_found = 0
    while True:
        if not pamet.page(name=page_name):
            return page_name
        default_names_found += 1
        page_name = f'{base_name} {default_names_found}'


def get_default_page():
    # desktop_config = get_config()
    # if 'home_page_id' in desktop_config:
    #     raise NotImplementedError()  # TODO: Load from id/url

    pages = list(pamet.pages())
    if not pages:
        return None
    else:
        page = pages[0]

    return page
