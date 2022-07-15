from __future__ import annotations
from pathlib import Path

from typing import List, Union
from urllib.parse import ParseResult, urlparse
from misli.basic_classes.point2d import Point2D
from misli.logging import get_logger
import pamet
from pamet.constants import ALIGNMENT_GRID_UNIT
# from pamet.desktop_app.config import get_config
log = get_logger(__name__)


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

    return None


class Url:
    def __init__(self, url: str):
        self._url = url
        self._parsed_url = urlparse(url)

    def is_internal(self):
        return self._parsed_url.scheme == 'pamet'

    def is_external(self):
        self._parsed_url.scheme in ['http', 'https', '']

    def is_custom_uri(self):
        return self._parsed_url.scheme not in ['pamet', 'http', 'https', '']

    def get_page(self):
        if self.is_internal():
            path = Path(self._parsed_url.path)

            if not path.parent != 'p':
                log.warning('Invalid url')
                return None

            return pamet.page(id=path.name)
        else:
            # A search for imported public/shared pages should be done here
            return None

    @property
    def hostname(self) -> Url:
        return self._parsed_url.hostname

    @property
    def netloc(self) -> Url:
        return self._parsed_url.netloc

    @property
    def path(self) -> Url:
        return self._parsed_url.path

    @property
    def scheme(self) -> Url:
        return self._parsed_url.scheme
