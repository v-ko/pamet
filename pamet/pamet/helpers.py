from __future__ import annotations
from datetime import datetime
from pathlib import Path

from typing import List, Tuple, Union
from urllib.parse import ParseResult, urlparse, urlunparse
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
    config = pamet.desktop_app.get_config()
    return pamet.page(id=config.home_page_id)


def current_time() -> datetime:
    return datetime.utcnow().astimezone().replace(microsecond=0)


class Url:
    def __init__(self, url: Union[Url, str]):
        if isinstance(url, Url):
            url = str(url)
        self._url: str = url
        self._parsed_url = urlparse(url)

    def __repr__(self) -> str:
        return urlunparse(self._parsed_url)

    def __eq__(self, other: Url) -> bool:
        return self._url == other._url

    def is_internal(self):
        return self._parsed_url.scheme == 'pamet'

    def is_external(self):
        if not str(self._url):
            return False
        return self._parsed_url.scheme in ['http', 'https', '']

    def has_web_schema(self):
        return self._parsed_url.scheme in ['http', 'https']

    def is_custom(self):
        return self._parsed_url.scheme not in ['pamet', 'http', 'https', '']

    def page_id(self):
        # This method should probably not be in this class
        if not self.is_internal():
            # A search for imported public/shared pages should be done here
            return None

        path = Path(self._parsed_url.path)
        parts = path.parts
        if not parts[1] == 'p' or len(parts) < 3:
            log.warning('Invalid url')
            return None

        return parts[2]

    def get_page(self):
        return pamet.page(id=self.page_id())

    def get_media_id(self):
        path = Path(self._parsed_url.path)
        parts = path.parts
        if not parts[1] == 'p' or not parts[3] == 'media' or len(parts) < 5:
            log.warning('Requested media id for url that has none')
            return None

        return parts[4]

    def get_anchor(self) -> Note | Tuple[float, Point2D] | None:
        fragment = self._parsed_url.fragment
        if fragment.startswith('note'):
            try:
                note_id = fragment.split('=')[1]
            except Exception:
                return None
            return pamet.find_one(id=note_id)
        elif fragment.startswith('eye_at'):
            try:
                center_tuple = fragment.split('=')[1]
                data = center_tuple.split('/')
                data = [float(c) for c in data]
                height = data[0]
                center = Point2D(data[1], data[2])
                return height, center
            except Exception:
                return None

    def with_anchor(self, anchor: str) -> Url:
        new_url = Url(self)
        new_url._parsed_url = new_url._parsed_url._replace(fragment=anchor)
        return new_url

    def is_empty(self):
        return not self._url

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
