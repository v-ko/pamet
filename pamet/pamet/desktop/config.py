
import os
import json
from pathlib import Path

from PySide2.QtCore import QStandardPaths

from misli import get_logger
log = get_logger(__name__)

# Това отива в Desktop модула или в самия main
default_data_path = QStandardPaths.writableLocation(
    QStandardPaths.GenericDataLocation)

default_config = {}

default_data_folder_path = Path(default_data_path) / 'misli' / 'pamet'
if not default_data_folder_path.exists():
    default_data_folder_path.mkdir(parents=True)

config_file_path = default_data_folder_path / 'config.json'
default_fs_repo_path = default_data_folder_path / 'repo'

default_config['repository_path'] = str(default_fs_repo_path)
# default_config['app_intro_dismissed'] = False


def _where_empty_set_defaults(config: dict):
    fixes_applied = False

    for k, v in default_config.items():
        if k not in config:
            log.info('Missing key "%s" in config. Setting default "%s"' %
                     (k, v))
            config[k] = v
            fixes_applied = True

    if fixes_applied:
        save_config(config)

    return config


def save_config(config: dict):
    with open(config_file_path, 'w') as cf:
        json.dump(config, cf)


def get_config():
    # Load the basic config
    if not os.path.exists(config_file_path):
        save_config(default_config)
        return default_config

    else:
        with open(config_file_path) as cf:
            config = json.load(cf)
            config = _where_empty_set_defaults(config)

            return config
