import os
from pathlib import Path
from PySide6.QtWidgets import QMessageBox
import click

import fusion
from fusion.libs.action import actions_log_channel
from fusion.libs.action.action_call import ActionCall, ActionRunStates
from fusion.logging import LOGGING_LEVEL, LoggingLevels
from pamet import channels as pamet_channels, commands, set_semantic_search_service

import pamet
from pamet import desktop_app
from pamet.actions import window as window_actions
from pamet.actions import other as other_actions
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.init_config import configure_for_qt
from pamet.model.page import Page

from pamet.services.backup import AnotherServiceAlreadyRunningException
from pamet.services.backup import FSStorageBackupService
from pamet.services.file_note_watcher import FileNoteWatcherService
from pamet.services.local_server import LocalServer
from pamet.services.other_pages_list_update import OtherPagesListUpdateService

from pamet.services.search.fuzzy import FuzzySearchService
from pamet.services.undo import UndoService
from pamet.storage import FSStorageRepository
from pamet.views.window.widget import WindowWidget

log = fusion.get_logger(__name__)


def raise_a_window():
    windows = [
        w for w in DesktopApp.instance().topLevelWidgets()
        if isinstance(w, WindowWidget)
    ]
    if windows:
        windows[0].show()
        windows[0].activateWindow()
        windows[0].raise_()


local_server_commands = {
    'grab_screen_snippet': commands.grab_screen_snippet,
    'raise_window': raise_a_window
}


@click.command()
@click.argument('path', type=click.Path(exists=True), required=False)
@click.option('--command', type=click.Choice(local_server_commands.keys()))
def main(path: str, command: str):
    # Check if another instance is running
    local_server = LocalServer(commands=local_server_commands)
    if local_server.another_instance_is_running():
        port = local_server.get_port_from_lock_file()
        if command:
            LocalServer.send_command(port, command)
        else:
            LocalServer.send_command(port, 'raise_window')
        return
    else:
        local_server.start()

    app = DesktopApp()
    app.aboutToQuit.connect(local_server.stop)

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

    # # Debug
    # misli_channels.state_changes_per_TLA_by_id.subscribe(
    #     lambda x: print(f'STATE_CHANGES_BY_ID CHANNEL: {x}'))

    start_page = pamet.default_page() or fs_repo.find_one(type=Page)
    if not start_page:
        start_page = other_actions.create_default_page()

    window_state = window_actions.new_browser_window()
    window = WindowWidget(initial_state=window_state)
    window.showMaximized()

    window_actions.new_browser_tab(window_state, start_page)

    search_service = FuzzySearchService(
        pamet_channels.entity_change_sets_per_TLA)
    search_service.load_all_content()
    pamet.set_search_service(search_service)

    other_page_list_service = OtherPagesListUpdateService()
    other_page_list_service.start()

    # Setup exception reporting for failed actions
    if LOGGING_LEVEL != LoggingLevels.DEBUG.value:

        def show_exception_for_failed_action(action_call: ActionCall):
            if action_call.run_state != ActionRunStates.FAILED:
                return
            title = f'Exception raised during action "{action_call.name}"'
            app.present_exception(exception=action_call.error, title=title)

        actions_log_channel.subscribe(show_exception_for_failed_action)

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

    # Experimental semantic search
    if repo_settings.semantic_search_enabled:
        from pamet.services.search.semantic import SemanticSearchService
        semantic_search_service = SemanticSearchService(
            data_folder=repo_path / '__semantic_index__',
            change_set_channel=pamet_channels.entity_change_sets_per_TLA)

        print('Loading semantic search index...')
        semantic_search_service.load_all_content()
        print('Semantic search index loaded')
        set_semantic_search_service(semantic_search_service)

    fusion.set_main_loop_exception_handler(
        lambda e: app.present_exception(e, title='Main loop exception')
    )

    # Watch files that have previews in notes and update them
    file_note_watcher_service = FileNoteWatcherService()
    file_note_watcher_service.start()
    app.aboutToQuit.connect(file_note_watcher_service.stop)

    return app.exec()


if __name__ == '__main__':
    main()
