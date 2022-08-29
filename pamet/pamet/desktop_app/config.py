from pathlib import Path

from PySide6.QtCore import QStandardPaths

from fusion import get_logger
from fusion.entity_library import entity_type
from pamet.config import PametConfig

log = get_logger(__name__)

user_data_path = QStandardPaths.writableLocation(
    QStandardPaths.GenericDataLocation)
pamet_data_folder_path = Path(user_data_path) / 'pamet'
pamet_data_folder_path.mkdir(parents=True, exist_ok=True)


@entity_type
class DesktopConfig(PametConfig):

    repository_path: str = pamet_data_folder_path / 'repo'
    media_store_path: str = pamet_data_folder_path / 'media_store'
    scripts_folder: str = pamet_data_folder_path / 'scripts'
    backup_folder: str = pamet_data_folder_path / 'backups'
    script_templates_folder: str = pamet_data_folder_path / 'script_templates'
    accepted_script_risks: bool = False
    run_in_terminal_prefix_posix: str = 'gnome-terminal -- '
    run_in_terminal_prefix_windows: str = 'powershell -noexit '
    record_all_changes: bool = False
