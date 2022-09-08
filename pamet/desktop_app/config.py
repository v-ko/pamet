from dataclasses import field
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from fusion import get_logger
from fusion.libs.entity import entity_type
from pamet.config import PametSettings

log = get_logger(__name__)

user_data_path = QStandardPaths.writableLocation(
    QStandardPaths.GenericDataLocation)
pamet_data_folder_path = Path(user_data_path) / 'pamet'
pamet_data_folder_path.mkdir(parents=True, exist_ok=True)


@entity_type
class UserDesktopSettings(PametSettings):

    repository_path: str = pamet_data_folder_path / 'repo'
    media_store_path: str = pamet_data_folder_path / 'media_store'
    scripts_folder: str = pamet_data_folder_path / 'scripts'
    script_templates_folder: str = pamet_data_folder_path / 'script_templates'
    accepted_script_risks: bool = False
    run_in_terminal_prefix_posix: str = 'gnome-terminal -- '
    run_in_terminal_prefix_windows: str = 'powershell -noexit '


@entity_type
class RepoSettings(PametSettings):
    repo_path: Path = field(repr=False,
                            default=None)
    backups_enabled: bool = True
    backup_folder: str = None
    home_page: str = None
    record_all_changes: bool = False

    def __post_init__(self):
        if self.repo_path is None:
            raise Exception

        if not self.backup_folder:
            self.backup_folder = self.repo_path / '.pamet' / 'backups'
