from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Union

from sivkit.logging import get_logger
from sivkit.util.point2d import Point2D

from pamet.constants import ALIGNMENT_GRID_UNIT

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
        raise Exception("Resource not found")
    return resource_path


def resource_dir(dir_subpath: str | Path):
    resources_folder = resources.files("pamet.resources")
    # if not dir_subpath:
    #     return resources_folder
    dir_subpath = Path(dir_subpath)
    return resources_folder / dir_subpath


def snap_to_grid(x: Union[float, Point2D]) -> Union[float, Point2D]:
    return round(x / ALIGNMENT_GRID_UNIT) * ALIGNMENT_GRID_UNIT
