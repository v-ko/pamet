from pathlib import Path
from fusion.libs.entity import entity_type
from pamet.model.text_note import TextNote

# SCRIPT = 'script'
SCRIPT_PATH = 'script_path'
COMMAND_ARGS = 'command_args'


@entity_type
class ScriptNote(TextNote):
    run_in_terminal: bool = True

    @property
    def script_path(self) -> Path | None:
        path_str = self.content.get(SCRIPT_PATH, '')
        return Path(path_str) if path_str else None

    @script_path.setter
    def script_path(self, script: Path | str):
        if script is None:
            self.content.pop(SCRIPT_PATH, None)
            return
        self.content[SCRIPT_PATH] = str(script)

    @property
    def command_args(self) -> str:
        return self.content.get(COMMAND_ARGS, '')

    @command_args.setter
    def command_args(self, script: str):
        self.content[COMMAND_ARGS] = script
