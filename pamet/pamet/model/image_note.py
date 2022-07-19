from typing import Union
from misli.entity_library import entity_type
from pamet.helpers import Url
from pamet.model.note import Note

IMAGE_URL = 'image_url'
LOCAL_IMAGE_URL = 'local_image_url'


@entity_type
class ImageNote(Note):

    @property
    def image_url(self) -> Url:
        try:
            url = self.content[IMAGE_URL]  #@IgnoreException
        except KeyError:
            url = ''
            self.content[IMAGE_URL] = url
        return Url(url)

    @image_url.setter
    def image_url(self, new_url: Union[Url, str, None]):
        if isinstance(new_url, Url):
            new_url = str(new_url)
        elif new_url is None:
            self.content.pop(IMAGE_URL, None)
            return
        self.content[IMAGE_URL] = new_url

    @property
    def local_image_url(self) -> Url:
        try:
            url = self.content[LOCAL_IMAGE_URL]  #@IgnoreException
        except KeyError:
            url = ''
            self.content[LOCAL_IMAGE_URL] = url
        return Url(url)

    @local_image_url.setter
    def local_image_url(self, new_url: Union[Url, str, None]):
        if isinstance(new_url, Url):
            new_url = str(new_url)
        elif new_url is None:
            self.content.pop(LOCAL_IMAGE_URL, None)
            return
        self.content[LOCAL_IMAGE_URL] = new_url
