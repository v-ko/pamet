from typing import Union
from fusion.util.point2d import Point2D
from fusion.util.rectangle import Rectangle
from fusion.libs.entity import entity_type
from pamet.util.url import Url
from pamet.model.note import Note

IMAGE_URL = 'image_url'
LOCAL_IMAGE_URL = 'local_image_url'
IMAGE_SIZE = 'image_size'
IMAGE_MD5 = 'image_md5'


@entity_type
class ImageNote(Note):

    @property
    def image_url(self) -> Url:
        return Url(self.content.get(IMAGE_URL, ''))

    @image_url.setter
    def image_url(self, new_url: Union[Url, str, None]):
        if isinstance(new_url, Url):
            new_url = str(new_url)
        if not new_url:
            self.content.pop(IMAGE_URL, None)
            return
        self.content[IMAGE_URL] = new_url

    @property
    def local_image_url(self) -> Url:
        return Url(self.content.get(LOCAL_IMAGE_URL, ''))

    @local_image_url.setter
    def local_image_url(self, new_url: Union[Url, str, None]):
        if isinstance(new_url, Url):
            new_url = str(new_url)
        if not new_url:
            self.content.pop(LOCAL_IMAGE_URL, None)
            return
        self.content[LOCAL_IMAGE_URL] = new_url

    @property
    def image_size(self) -> Point2D:
        if IMAGE_SIZE in self.metadata:
            return Point2D(*self.metadata[IMAGE_SIZE])
        return None

    @image_size.setter
    def image_size(self, size: Point2D):
        self.metadata[IMAGE_SIZE] = size.as_tuple()

    @property
    def image_md5(self) -> Point2D:
        if IMAGE_MD5 in self.metadata:
            return self.metadata[IMAGE_MD5]
        return None

    @image_md5.setter
    def image_md5(self, md5sum: Point2D):
        self.metadata[IMAGE_MD5] = md5sum

    def image_rect(self) -> Rectangle:
        note_rect: Rectangle = self.rect()
        image_AR = self.image_size.x() / self.image_size.y()
        note_AR = note_rect.width() / note_rect.height()

        if note_AR > image_AR:
            width = image_AR * note_rect.height()
            height = note_rect.height()
            return Point2D(width, height)
        else:
            width = note_rect.width()
            height = note_rect.width() / image_AR
            return Point2D(width, height)
