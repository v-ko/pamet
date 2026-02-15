from dataclasses import field
from pathlib import Path

from fusion.libs.entity import entity_type
from pamet.config import PametSettings
from PySide6.QtCore import QStandardPaths

from fusion import get_logger

log = get_logger(__name__)

user_data_path = QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation)
DEFAULT_DATA_FOLDER_PATH = Path(user_data_path) / "pamet"
DEFAULT_DATA_FOLDER_PATH.mkdir(parents=True, exist_ok=True)


@entity_type
class UserDesktopSettings(PametSettings):
    recent_projects: list[str] = field(default_factory=list)
    scripts_folder: str = str(DEFAULT_DATA_FOLDER_PATH / "scripts")
    script_templates_folder: str = str(DEFAULT_DATA_FOLDER_PATH / "script_templates")
    accepted_script_risks: bool = False
    run_in_terminal_prefix_posix: str = "gnome-terminal -- "
    run_in_terminal_prefix_windows: str = "powershell -noexit "
    static_export_folder: str = str(DEFAULT_DATA_FOLDER_PATH / "static_export")

    @property
    def repository_path(self) -> str:
        if self.recent_projects:
            return self.recent_projects[0]
        return str(DEFAULT_DATA_FOLDER_PATH / "repo")

    @repository_path.setter
    def repository_path(self, path: str):
        if not path:
            return
        path_str = str(path)
        filtered = [p for p in self.recent_projects if p and p != path_str]
        self.recent_projects = [path_str] + filtered


@entity_type
class RepoSettings(PametSettings):
    repo_path: Path = field(repr=False, default=None)
    backups_enabled: bool = True
    backup_folder: str | None = None
    home_page: str | None = None
    record_all_changes: bool = False
    semantic_search_enabled: bool = False
    media_store_path: str | None = None

    def __post_init__(self):
        if self.repo_path is None:
            raise Exception

        if not self.backup_folder:
            self.backup_folder = str(self.repo_path / ".pamet" / "backups")

        if not self.media_store_path:
            self.media_store_path = str(self.repo_path / ".pamet" / "media")
