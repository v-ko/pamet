import os
from pathlib import Path

import misli
from misli.gui import channels as misli_channels
from pamet import channels as pamet_channels

import pamet
from pamet import desktop_app
from pamet.actions import window as window_actions
from pamet.actions import other as other_actions
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.helpers import configure_for_qt
from pamet.services.backup import FSStorageBackupService
from pamet.services.search.fuzzy import FuzzySearchService
from pamet.storage import FSStorageRepository
from pamet.views.window.widget import WindowWidget

log = misli.get_logger(__name__)

# @action('main.create_window')
# def create_window():


def main():
    misli.line_spacing_in_pixels = 20
    app = DesktopApp()

    desktop_app.set_app(app)
    configure_for_qt()

    # Load the config
    config = desktop_app.get_config()
    # If there's changes after the load it means that some default is not saved
    # to disk or some other irregularity has been handled by the config class
    if config.changes_present:
        desktop_app.save_config(config)

    # Init the repo
    repo_path = Path(config.repository_path)
    log.info('Using repository: %s' % repo_path)

    # # Testing - restore repo changes
    # backup_folder = repo_path / '__legacy_pages_backup__'
    # backup_page_names = []
    # new_paths_by_old_path = {}
    # for file in backup_folder.iterdir():
    #     if file.name.endswith('.json.backup'):
    #         new_path = file.parent.parent / file.with_suffix('').name
    #         new_paths_by_old_path[file] = new_path

    #         page_data = json.loads(file.read_text())
    #         page_name = file.with_suffix('').with_suffix('').name
    #         backup_page_names.append(page_name)

    # # Read all page names in the repo
    # page_paths_by_name = {}
    # for file in repo_path.iterdir():
    #     if file.is_file() and file.name.endswith('.pam4.json'):
    #         page_data = json.loads(file.read_text())
    #         name = page_data['name']
    #         page_paths_by_name[name] = file

    # # Delete all previously imported (by name matching)
    # for page_name in backup_page_names:
    #     if page_name in page_paths_by_name:
    #         page_paths_by_name[page_name].unlink()
    #     else:
    #         pass

    # # Restore the backups
    # for old_path, new_path in new_paths_by_old_path.items():
    #     old_path.rename(new_path)


    if os.path.exists(repo_path):
        fs_repo = FSStorageRepository.open(repo_path,
                                           queue_save_on_change=True)
    else:
        fs_repo = FSStorageRepository.new(repo_path, queue_save_on_change=True)

    pamet.set_sync_repo(fs_repo)
    # There should be a better place to do call the validity checks I guess
    pamet.model.arrow_validity_check()

    # Debug
    misli_channels.state_changes_per_TLA_by_id.subscribe(
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

    search_service = FuzzySearchService(
        pamet_channels.entity_change_sets_per_TLA)
    search_service.load_all_content()
    pamet.set_search_service(search_service)

    backup_service = FSStorageBackupService(
        backup_folder=config.backup_folder,
        change_set_channel=pamet_channels.entity_change_sets_per_TLA,
        record_all_changes=True)
    if not backup_service.start():
        log.info('Backup service not started. '
                 'Probably another instance is running')
    else:
        app.aboutToQuit.connect(backup_service.stop)

    return app.exec()


if __name__ == '__main__':
    main()
