
import os
import json

from PySide2.QtCore import QStandardPaths

from misli import get_logger
log = get_logger(__name__)

# Това отива в Desktop модула или в самия main
default_data_path = QStandardPaths.writableLocation(
    QStandardPaths.GenericDataLocation)

default_config = {}
default_fs_repo_path = os.path.join(default_data_path, 'default_repository')
default_config['repository_path'] = default_fs_repo_path
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
    config_file_path = os.path.join(default_data_path, 'config.json')

    with open(config_file_path, 'w') as cf:
        json.dump(config, cf)


def get_config():
    config_file_path = os.path.join(default_data_path, 'config.json')
    # Load the basic config
    if not os.path.exists(config_file_path):
        save_config(default_config)
        return default_config

    else:
        with open(config_file_path) as cf:
            config = json.load(cf)
            config = _where_empty_set_defaults(config)

            return config
