from pathlib import Path
from typing import Union

from PySide6.QtGui import QImage

from fusion.util import get_new_id

from pamet.desktop_app.util import jpeg_blob_from_image
from pamet.util.url import Url
from slugify import slugify


class MediaStore:

    def __init__(self, media_root: Union[Path, str]):
        self.media_root = Path(media_root)

    def path_for_internal_uri(self, uri: Union[Url, str]) -> Union[Path, None]:
        uri = Url(uri)

        if not uri.is_internal():
            raise Exception('The given URI is not internal')

        cache_subfolder_name = uri.get_page_id()
        media_id = uri.get_media_id()
        return self.media_root / cache_subfolder_name / media_id

    def save_blob(self,
                  blob: bytes,
                  format: str = '',
                  cache_subfolder_name: str = '__common__',
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
        file_path = self.media_root / cache_subfolder_name
        file_path.mkdir(parents=True, exist_ok=True)
        file_path = file_path / file_name

        try:
            bytes_written = file_path.write_bytes(blob)
        except Exception:
            return None

        if not bytes_written:
            return None

        return Url(f'pamet:///p/{cache_subfolder_name}/media/{file_name}')

    def save_image(self,
                   image: QImage,
                   format: str = 'jpg',
                   cache_subfolder_name: str = '__images__',
                   source_uri: Union[Url, str] = None) -> Url:
        if image.isNull():
            raise Exception('The given image is null')

        blob = jpeg_blob_from_image(image)
        return self.save_blob(blob, format, cache_subfolder_name, source_uri)
