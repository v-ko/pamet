import os
import signal

from PySide6.QtWidgets import QWidget

import misli

from pamet import default_key_bindings
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.config import get_config
from pamet.storage import FSStorageRepository
from pamet.actions.desktop import new_browser_window_ensure_page

log = misli.get_logger(__name__)
signal.signal(signal.SIGINT, signal.SIG_DFL)


def main():
    misli.line_spacing_in_pixels = 20
    config = get_config()
    repo_path = config['repository_path']
    log.info('Using repository: %s' % repo_path)

    # # Testing - restore repo changes
    # for f in os.scandir(repo_path):
    #     if f.name.endswith('backup'):
    #         os.rename(f.path, f.path[:-7])
    #
    #     if f.name.endswith('misl.json'):
    #         os.remove(f.path)

    if os.path.exists(repo_path):
        fs_repo = FSStorageRepository.open(repo_path)
    else:
        fs_repo = FSStorageRepository.new(repo_path)

    misli.set_repo(fs_repo)

    desktop_app = DesktopApp()

    # desktop_app.processEvents()

    misli.configure_for_qt()
    misli.gui.key_binding_manager.apply_config(default_key_bindings)
    misli.gui.queue_action(new_browser_window_ensure_page)
    return desktop_app.exec_()
