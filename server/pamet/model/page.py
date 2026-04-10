from datetime import datetime
from pathlib import PurePosixPath

import attrs
from fusion import Entity, entity_type
from fusion.util import current_time, timestamp


@entity_type
class Page(Entity):
    path: str = ""
    created: str = attrs.Factory(lambda: timestamp(current_time()))
    modified: str = attrs.Factory(lambda: timestamp(current_time()))

    def __repr__(self):
        return f"<Page id={self.id} path={self.path}>"

    @property
    def name(self) -> str:
        return PurePosixPath(self.path).stem if self.path else ""

    @property
    def folder(self) -> str:
        parent = PurePosixPath(self.path).parent.as_posix() if self.path else ""
        return "" if parent == "." else parent

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
