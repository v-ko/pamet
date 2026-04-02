from fusion.libs.entity import entity_type

from pamet.model.note import Note


@entity_type
class CardNote(Note):
    """Unified note type matching TS CardNote.

    Content keys: text, url, image_id
    Metadata keys: is_project_index_header
    Style keys: color_role, background_color_role
    """

    # --- Text ---
    @property
    def text(self) -> str:
        return self.content.get("text", "")

    @text.setter
    def text(self, new_text: str):
        self.content["text"] = new_text

    # --- URL (general link) ---
    @property
    def url(self) -> str:
        return self.content.get("url", "")

    @url.setter
    def url(self, new_url: str | None):
        if not new_url:
            self.content.pop("url", None)
            return
        self.content["url"] = new_url

    # --- Image ---
    @property
    def image_id(self) -> str | None:
        return self.content.get("image_id")

    @image_id.setter
    def image_id(self, item_id: str | None):
        if item_id is None:
            self.content.pop("image_id", None)
        else:
            self.content["image_id"] = item_id
