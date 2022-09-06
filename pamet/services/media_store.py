from pathlib import Path
from typing import Union

from fusion.util import get_new_id

import pamet
from pamet.util.url import Url
from pamet.model.page import Page
from slugify import slugify


class MediaStore:

    def __init__(self, media_root: Union[Path, str]):
        self.media_root = Path(media_root)

    def path_for_internal_uri(self, uri: Union[Url, str]) -> Union[Path, None]:
        uri = Url(uri)

        if not uri.is_internal():
            raise Exception('The given URI is not internal')

        page = pamet.page(uri.get_page_id())
        media_id = uri.get_media_id()
        return self.media_root / page.id / media_id

    def save_blob(self,
                  page_id: str,
                  blob: bytes,
                  format: str,
                  source_uri: Union[Url, str] = None) -> Url:
        """Saves the given blob to a file in the media store.

        Each page has a separate folder. The file name consists of a slug
        extracted from the source_uri, the image id and an extension
        equal to the given format."""
        if not blob:
            return None

        # Generate the source_slug
        source_slug = ''
        if source_uri:
            source_uri = Url(source_uri)
            source_slug = Path(source_uri.path).name
            source_slug = slugify(source_slug, max_length=50)

        file_name = f'{source_slug}[{get_new_id()}]'
        if format:
            file_name += f'.{format}'
        file_path = self.media_root / page_id
        file_path.mkdir(parents=True, exist_ok=True)
        file_path = file_path / file_name

        try:
            bytes_written = file_path.write_bytes(blob)
        except Exception:
            return None

        if not bytes_written:
            return None

        return Url(f'pamet:///p/{page_id}/media/{file_name}')
