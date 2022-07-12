import os

import misli
from misli.gui import channels

import pamet
from pamet.actions import window as window_actions
from pamet.actions import other as other_actions
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.config import get_config
from pamet.persistence_manager import PersistenceManager
from pamet.storage import FSStorageRepository
from pamet.views.window.widget import WindowWidget

log = misli.get_logger(__name__)

# @action('main.create_window')
# def create_window():


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
        fs_repo = FSStorageRepository.open(repo_path,
                                           queue_save_on_change=True)
    else:
        fs_repo = FSStorageRepository.new(repo_path, queue_save_on_change=True)

    pamet.set_sync_repo(fs_repo)
    misli.configure_for_qt()
    pamet.configure_for_qt()

    # Debug
    channels.state_changes_by_id.subscribe(
        lambda x: print(f'STATE_CHANGES_BY_ID CHANNEL: {x}'))

    desktop_app = DesktopApp()

    start_page = pamet.helpers.get_default_page() or pamet.page()
    if not start_page:
        start_page = other_actions.create_default_page()

    window_state = window_actions.new_browser_window()
    window = WindowWidget(initial_state=window_state)
    window.showMaximized()

    misli.call_delayed(window_actions.new_browser_tab,
                       args=[window_state, start_page])

    desktop_app.focusChanged.connect(
        lambda w1, w2: print(f'Focus changed from {w1} to {w2}'))
    return desktop_app.exec()


if __name__ == '__main__':
    main()
