from misli import get_logger
from misli import entity_type
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
    def url(self, new_url):
        if URL in self.content and self.content[URL] == new_url:
            return

        self.content[URL] = new_url
