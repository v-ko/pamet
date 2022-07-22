import os

import misli
from misli.gui import channels

import pamet
from pamet.actions import window as window_actions
from pamet.actions import other as other_actions
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.helpers import configure_for_qt
from pamet.persistence_manager import PersistenceManager
from pamet.storage import FSStorageRepository
from pamet.views.window.widget import WindowWidget

log = misli.get_logger(__name__)

# @action('main.create_window')
# def create_window():


def main():
    misli.line_spacing_in_pixels = 20
    app = DesktopApp()
    pamet.desktop_app.set_app(app)
    configure_for_qt()

    # Load the config
    config = pamet.desktop_app.get_config()
    # If there's changes after the load it means that some default is not saved
    # to disk or some other irregularity has been handled by the config class
    if config.changes_present:
        pamet.desktop_app.save_config(config)

    # Init the repo
    repo_path = config.repository_path
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
    # There should be a better place to do call the validity checks I guess
    pamet.model.arrow_validity_check()

    # Debug
    channels.state_changes_by_id.subscribe(
        lambda x: print(f'STATE_CHANGES_BY_ID CHANNEL: {x}'))

    start_page = pamet.helpers.get_default_page() or pamet.page()
    if not start_page:
        start_page = other_actions.create_default_page()

    window_state = window_actions.new_browser_window()
    window = WindowWidget(initial_state=window_state)
    window.showMaximized()

    misli.call_delayed(window_actions.new_browser_tab,
                       args=[window_state, start_page])

    app.focusChanged.connect(
        lambda w1, w2: print(f'Focus changed from {w1} to {w2}'))
    return app.exec()


if __name__ == '__main__':
    main()
