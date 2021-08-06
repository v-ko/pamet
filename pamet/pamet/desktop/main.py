import os
import signal

import misli
from misli.gui.desktop import QtMainLoop

import pamet
from pamet.desktop.app import DesktopApp
from pamet.desktop.config import get_config
from pamet.services.file_system_storage import FSStorageRepository
from pamet.desktop.usecases import new_browser_window_ensure_page

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
        fs_repo = FSStorageRepository.create(repo_path)

    if not fs_repo:
        log.error('Error initializing repository. Exiting.')
        return

    for page_id in fs_repo.page_ids():
        page, notes = fs_repo.page_with_notes(page_id)
        pamet.load_page(page, notes)

    # pamet.set_repo(fs_repo, 'all')
    misli.set_main_loop(QtMainLoop())

    misli.subscribe(pamet.PAGES_CHANNEL, fs_repo.save_changes)
    misli.subscribe(pamet.ALL_NOTES_CHANNEL, fs_repo.save_changes)

    desktop_app = DesktopApp()
    misli.call_delayed(new_browser_window_ensure_page, 0)

    return desktop_app.exec_()