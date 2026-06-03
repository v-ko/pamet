from sivkit.libs.model import entity_type

from pamet.model.note import ImageReference, Note, NoteContent, PageReference


@entity_type
class CardNote(Note[NoteContent]):
    """Unified note type matching TS CardNote.

    Content keys: text, url, page_ref, image
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
    def image(self) -> ImageReference | None:
        return self.content.get("image")

    @image.setter
    def image(self, ref: ImageReference | None):
        if ref is None:
            self.content.pop("image", None)
        else:
            self.content["image"] = ref

    # --- Page ref (internal link to another page) ---
    @property
    def page_ref(self) -> PageReference | None:
        return self.content.get("page_ref")

    @page_ref.setter
    def page_ref(self, ref: PageReference | None):
        if ref is None:
            self.content.pop("page_ref", None)
        else:
            self.content["page_ref"] = ref
