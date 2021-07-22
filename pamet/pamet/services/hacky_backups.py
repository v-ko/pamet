import shutil
from pathlib import Path
from typing import Union


def backup_page_hackily(page_path: Union[str, Path]):
    """
    Saves the page in a page_name/hacky_backup folder with an id as a added
    file suffix.
    """
    if type(page_path) != Path:
        page_path = Path(page_path)

    LATEST = "__latest__"
    backup_folder_path = page_path.parent / page_path.stem / "hacky_backups"
    backup_folder_path.mkdir(parents=True, exist_ok=True)

    latest_index = 0
    latest_index_file_name = backup_folder_path / LATEST
    if latest_index_file_name.exists():
        with open(latest_index_file_name) as latest_index_file:
            latest_index = int(str(latest_index_file.read()).strip())

    current_index = latest_index + 1

    backup_path = backup_folder_path / page_path.name
    backup_path = backup_path.with_suffix(
        page_path.suffix + str(current_index))

    shutil.copy(page_path, backup_path)

    with open(latest_index_file_name, "w") as latest_index_file:
        latest_index_file.write(str(current_index))
