from pathlib import Path
from misli.entity_library import entity_type
from pamet.model.text_note import TextNote

SCRIPT = 'script'
SCRIPT_PATH = 'script_path'
SCRIPT_ARGS = 'script_args'


@entity_type
class ScriptNote(TextNote):
    run_in_terminal: bool = True
    script_args_str: str = ''

    @property
    def script(self) -> str:
        return self.content.get(SCRIPT, '')

    @script.setter
    def script(self, script: str):
        self.content[SCRIPT] = script

    @property
    def script_path(self) -> Path | None:
        path_str = self.content.get(SCRIPT, '')
        return Path(path_str) if path_str else None

    @script_path.setter
    def script_path(self, script: Path | str):
        if script is None:
            self.content.pop(SCRIPT_PATH, None)
            return
        self.content[SCRIPT] = str(script)
