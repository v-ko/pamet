from __future__ import annotations

from typing import TypedDict, cast

import attrs
from fusion.libs.entity import entity_type

from pamet.model.page_child import PageChild


class FileItemContent(TypedDict, total=False):
    hash: str


class FileItemMetadata(TypedDict, total=False):
    size: int
    mime_type: str


@entity_type
class FileItem(PageChild):
    path: str = ""
    content: FileItemContent = attrs.Factory(lambda: cast(FileItemContent, {}))
    metadata: FileItemMetadata = attrs.Factory(lambda: cast(FileItemMetadata, {}))

    @property
    def content_hash(self) -> str:
        return self.content.get("hash", "")


class ImageItemMetadata(FileItemMetadata, total=False):
    width: int
    height: int


@entity_type
class ImageItem(FileItem):
    """Image file item — extends FileItem with width/height metadata.

    Matches TS ImageItem / ImageItemData.
    """

    @property
    def width(self) -> int:
        return self.metadata.get("width", 0)  # type: ignore[typeddict-item]

    @property
    def height(self) -> int:
        return self.metadata.get("height", 0)  # type: ignore[typeddict-item]
