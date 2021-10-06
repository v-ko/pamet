import os
import signal

import misli
from misli.gui.qt_main_loop import QtMainLoop
from misli.gui import ENTITY_CHANGE_CHANNEL

import pamet
from pamet.desktop.app import DesktopApp
from pamet.desktop.config import get_config
from pamet.services.file_system_storage import FSStorageRepository
from pamet.desktop.usecases import new_browser_window_ensure_page

log = misli.get_logger(__name__)
signal.signal(signal.SIGINT, signal.SIG_DFL)


@misli.gui.action('create_desktop_app')
def create_desktop_app():
    return DesktopApp()


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

    if not fs_repo:
        log.error('Error initializing repository. Exiting.')
        return

    misli.set_repo(fs_repo)
    misli.set_main_loop(QtMainLoop())

    desktop_app = create_desktop_app()
    misli.call_delayed(new_browser_window_ensure_page, 0)

    return desktop_app.exec_()