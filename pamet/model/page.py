from dataclasses import field
from datetime import datetime
from fusion import Entity, entity_type
from pamet.util.url import Url
from fusion.util import current_time, timestamp


@entity_type
class Page(Entity):
    name: str = ''
    created: str = field(default_factory=lambda: timestamp(current_time()))
    modified: str = field(default_factory=lambda: timestamp(current_time()))

    def __repr__(self):
        return f'<Page gid={self.gid()} name={self.name}>'

    def url(self):
        return Url(f'pamet:///p/{self.id}')

    @property
    def datetime_created(self) -> datetime:
        return datetime.fromisoformat(self.created)

    @datetime_created.setter
    def datetime_created(self, new_dt: datetime):
        self.created = timestamp(new_dt)

    @property
    def datetime_modified(self) -> datetime:
        return datetime.fromisoformat(self.modified)

    @datetime_modified.setter
    def datetime_modified(self, new_dt: datetime):
        self.modified = timestamp(new_dt)
