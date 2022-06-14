from pathlib import Path
from urllib.parse import ParseResult, urlparse
from misli import get_logger
from misli import entity_type
import pamet
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

    @property
    def parsed_url(self) -> ParseResult:
        return urlparse(self.url)

    def is_custom_uri(self) -> bool:
        return self.parsed_url.scheme not in ['pamet', 'http', 'https', '']

    def linked_page(self):
        if self.parsed_url.scheme == 'pamet':
            # It's a page in the local repo (i.e. internal link, not shared)
            if self.parsed_url.hostname or self.parsed_url.netloc:
                log.warning('Redundant check failed')
                return None

            path = Path(self.parsed_url.path)

            if not path.parent != 'p':
                log.warning('Invalid url')
                return None

            return pamet.page(id=path.name)

        else:
            # A search for imported public/shared pages should be done here
            return None
