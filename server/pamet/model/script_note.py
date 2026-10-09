from typing import TypedDict

from sivkit.libs.model import entity_type

from pamet.model.note import Note


class ScriptContent(TypedDict, total=False):
    text: str
    script_path: str
    command_args: str
    run_in_terminal: bool
    working_directory: str


@entity_type
class ScriptNote(Note[ScriptContent]):
    """A note that runs a command/script via the desktop backend.

    Content schema is independent of NoteContent: ScriptNote stores
    its own per-subtype payload and does not inherit text/url/image
    fields from CardNote.
    """

    # --- text (display label on the note) ---
    @property
    def text(self) -> str:
        return self.content.get("text", "")

    @text.setter
    def text(self, v: str) -> None:
        self.content["text"] = v

    # --- script_path ---
    @property
    def script_path(self) -> str:
        return self.content.get("script_path", "")

    @script_path.setter
    def script_path(self, v: str) -> None:
        self.content["script_path"] = v

    # --- command_args ---
    @property
    def command_args(self) -> str:
        return self.content.get("command_args", "")

    @command_args.setter
    def command_args(self, v: str) -> None:
        self.content["command_args"] = v

    # --- run_in_terminal ---
    @property
    def run_in_terminal(self) -> bool:
        return bool(self.content.get("run_in_terminal", False))

    @run_in_terminal.setter
    def run_in_terminal(self, v: bool) -> None:
        self.content["run_in_terminal"] = v

    # --- working_directory ---
    @property
    def working_directory(self) -> str:
        return self.content.get("working_directory", "")

    @working_directory.setter
    def working_directory(self, v: str) -> None:
        self.content["working_directory"] = v
