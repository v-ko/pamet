from __future__ import annotations

from pathlib import Path
from typing import Union, Tuple
from urllib.parse import urlparse, urlunparse

from fusion.logging import get_logger
from fusion.util import Point2D

import pamet
from pamet.constants import DEFAULT_EYE_HEIGHT

log = get_logger(__name__)


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

    def get_page_id(self):
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
                note_own_id = fragment.split('=')[1]
            except Exception:
                return None
            return pamet.note(self.get_page_id(), own_id=note_own_id)
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

    def with_anchor(self,
                    anchor: str = None,
                    eye_height: float = None,
                    eye_pos: Point2D = None,
                    note: Note = None) -> Url:
        eye_is_specified = bool(eye_height is not None or eye_pos)
        if bool(anchor) + eye_is_specified + bool(note) != 1:
            raise Exception(
                'Specifiy either eye_at, note or the anchor string')

        if eye_is_specified:
            if eye_height is None:
                eye_height = DEFAULT_EYE_HEIGHT
            elif eye_pos is None:
                eye_pos = Point2D(0, 0)
            anchor = f'eye_at={eye_height}/{eye_pos.x()}/{eye_pos.y()}'

        if note:
            anchor = f'note={note.own_id}'

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
