import json
import os
from pathlib import Path
from PySide6.QtWidgets import QMessageBox
import click

import fusion
# from fusion.gui import channels as misli_channels
from pamet import channels as pamet_channels

import pamet
from pamet import desktop_app
from pamet.actions import window as window_actions
from pamet.actions import other as other_actions
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.util import configure_for_qt
from pamet.model.page import Page

from pamet.services.backup import AnotherServiceAlreadyRunningException, FSStorageBackupService

from pamet.services.search.fuzzy import FuzzySearchService
from pamet.services.undo import UndoService
from pamet.storage import FSStorageRepository
from pamet.views.window.widget import WindowWidget

log = fusion.get_logger(__name__)


@click.command()
@click.argument('path', type=click.Path(exists=True), required=False)
def main(path: str):
    app = DesktopApp()
    configure_for_qt(app)
    # Load the config
    user_config = desktop_app.get_user_settings()
    # If there's changes after the load it means that some default is not saved
    # to disk or some other irregularity has been handled by the config class
    if user_config.changes_present:
        desktop_app.save_user_settings(user_config)

    # Init the repo
    if path:
        repo_path = Path(path)
    else:
        repo_path = Path(user_config.repository_path)
    log.info('Using repository: %s' % repo_path)

    # Testing - restore legacy backups

    # # V2
    # v2_backup_folder = repo_path / '__v2_legacy_pages_backup__'
    # for file in v2_backup_folder.iterdir():

    #     v3_file_in_repo = file.parent.parent / file.name
    #     v3_file_in_repo = v3_file_in_repo.with_suffix('').with_suffix('.json')

    #     if v3_file_in_repo.exists():
    #         v3_file_in_repo.unlink()
    #     restore_path = file.parent.parent / file.name
    #     restore_path = restore_path.with_suffix('')
    #     file.rename(restore_path)

    # for file in repo_path.iterdir():
    #     if file.name.endswith('.pam4.json'):
    #         file.unlink()

    # # V3
    # v3_backup_folder = repo_path / '__v3_legacy_pages_backup__'
    # backup_page_names = []
    # new_paths_by_old_path = {}
    # for file in v3_backup_folder.iterdir():
    #     if file.name.endswith('.backup'):
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
        legacy_page_paths = fs_repo.process_legacy_pages()
        fs_repo.load_all_pages()

        # Checksum legacy pages and fix internal links in them
        for page_path in legacy_page_paths:
            page_id = fs_repo.id_from_page_path(page_path)
            page = fs_repo.find_one(id=page_id)

            fs_repo.checksum_imported_page_notes(page)
            fs_repo.fix_legacy_page_internal_links(page)
    else:
        fs_repo = FSStorageRepository.new(repo_path, queue_save_on_change=True)

    repo_settings = desktop_app.get_repo_settings(repo_path)
    if repo_settings.changes_present:
        desktop_app.save_repo_settings(repo_settings)

    pamet.set_sync_repo(fs_repo)
    pamet.set_undo_service(
        UndoService(pamet_channels.entity_change_sets_per_TLA))

    # There should be a better place to do call the validity checks I guess
    # pamet.model.arrow_validity_check()

    # # Debug
    # misli_channels.state_changes_per_TLA_by_id.subscribe(
    #     lambda x: print(f'STATE_CHANGES_BY_ID CHANNEL: {x}'))

    start_page = pamet.default_page() or fs_repo.find_one(type=Page)
    if not start_page:
        start_page = other_actions.create_default_page()

    window_state = window_actions.new_browser_window()
    window = WindowWidget(initial_state=window_state)
    window.showMaximized()

    # fusion.call_delayed(window_actions.new_browser_tab,
    #                    args=[window_state, start_page])
    window_actions.new_browser_tab(window_state, start_page)

    search_service = FuzzySearchService(
        pamet_channels.entity_change_sets_per_TLA)
    search_service.load_all_content()
    pamet.set_search_service(search_service)

    if repo_settings.backups_enabled:
        backup_service = FSStorageBackupService(
            backup_folder=repo_settings.backup_folder,
            repository=fs_repo,
            changeset_channel=pamet_channels.entity_change_sets_per_TLA,
            record_all_changes=repo_settings.record_all_changes)

        service_started = False
        try:
            backup_service.start()
            service_started = True
        except AnotherServiceAlreadyRunningException:
            log.info('Backup service not started. '
                     'Probably another instance is running')
            reply = QMessageBox.question(
                window, 'Backup service conflict',
                'A backup service lock is present. If you\'re sure there\'s '
                'no other instances running on the same repo - '
                'press Yes to override.')
            if reply == QMessageBox.StandardButton.Yes:
                backup_service.service_lock_path().unlink()
                backup_service.start()
                service_started = True

        if service_started:
            app.aboutToQuit.connect(backup_service.stop)

    return app.exec()


if __name__ == '__main__':
    main()
