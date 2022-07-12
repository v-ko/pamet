from pathlib import Path
from urllib.parse import ParseResult, urlparse
from misli import get_logger
from misli import entity_type
import pamet
from pamet.helpers import Url
from pamet.model.page import Page
from pamet.model.text_note import TextNote

log = get_logger(__name__)

URL = 'url'


@entity_type
class AnchorNote(TextNote):
    def __post_init__(self):
        super().__post_init__()

        if URL not in self.content:
            self.content[URL] = ''

    @property
    def url(self) -> str:
        return self.content[URL]

    @url.setter
    def url(self, new_url: str):
        self.content[URL] = new_url

    def is_custom_uri(self) -> bool:
        return Url(self.url).is_custom_uri()

    def linked_page(self) -> Page:
        return Url(self.url).get_page()

    def is_external_link(self) -> bool:
        return Url(self.url).is_external()

    def is_internal_link(self) -> bool:
        return Url(self.url).is_internal()
