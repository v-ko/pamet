from __future__ import annotations
from importlib import resources
from pathlib import Path

from typing import Union
from fusion.util.point2d import Point2D
from fusion.logging import get_logger
import pamet
from pamet.constants import ALIGNMENT_GRID_UNIT
from pamet.model.page import Page

log = get_logger(__name__)


def resource_path(subpath: Union[str, Path]):
    # resource_dir_path = Path(__file__).parent.parent / 'resources'
    # resource_path = resource_dir_path / Path(subpath)
    subpath = Path(subpath)
    # resource_path = resources.path('pamet.resources', subpath)
    resource_path = resource_dir(subpath.parent) / subpath.name

    # if subpath.startswith('/'):
    #     subpath = subpath[1:]

    if not resource_path.exists():
        raise Exception('Resource not found')
    return resource_path


def resource_dir(dir_subpath: str | Path):
    resources_folder = resources.files('pamet.resources')
    # if not dir_subpath:
    #     return resources_folder
    dir_subpath = Path(dir_subpath)
    return resources_folder / dir_subpath


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


# Validity checks
def arrow_validity_check():
    """Removes arrows with missing anchor notes. Must be performed after
    the repo has been initialized."""
    from pamet.model.arrow import Arrow

    # Validity check on the arrow note anchors
    # If the note, that the anchor points to, is missing - skip arrow
    invalid_arrows = []
    for arrow in pamet.find(type=Arrow):
        tail_note = pamet.note(arrow.page_id, arrow.get_tail_note_own_id())
        head_note = pamet.note(arrow.page_id, arrow.get_head_note_own_id())
        if (arrow.has_tail_anchor() and not tail_note) or\
                (arrow.has_head_anchor() and not head_note):

            invalid_arrows.append(arrow)

    for arrow in invalid_arrows:
        log.error('Removing arrow because of an invalid note anchor: '
                  f'{arrow}')
        pamet.remove_arrow(arrow)
