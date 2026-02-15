import os
from pathlib import Path

import click

# from fusion import actions_log_channel
from fusion.libs.action.action_call import ActionCall, ActionRunStates
from fusion.logging import LOGGING_LEVEL, LoggingLevels
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.init_config import configure_for_qt
from pamet.desktop_app.screen_snippet import grab_screen_snippet
from pamet.desktop_app.web_shell import WebShellWindow
from pamet.model.page import Page
from pamet.services.backup import (
    AnotherServiceAlreadyRunningException,
    FSStorageBackupService,
)
from pamet.services.media_backend import MediaStorageBackendService
from pamet.services.media_store import MediaStore
from pamet.services.project_folder_manager import ProjectFolderManager
from pamet.services.rest_api.desktop import DesktopServer
from pamet.services.rest_api.routes import desktop as desktop_routes_module
from pamet.services.search.fuzzy import FuzzySearchService
from pamet.services.undo import UndoService
from pamet.storage import FSStorageRepository
from PySide6.QtWidgets import QMessageBox

import fusion
import pamet
from pamet import channels as pamet_channels
from pamet import desktop_app, set_semantic_search_service

log = fusion.get_logger(__name__)


def raise_a_window():
    windows = [
        w
        for w in DesktopApp.instance().topLevelWidgets()
        if isinstance(w, WebShellWindow)
    ]
    if windows:
        windows[0].show()
        windows[0].activateWindow()
        windows[0].raise_()


local_server_commands = {
    "grab_screen_snippet": grab_screen_snippet,
    "raise_window": raise_a_window,
}


@click.command()
@click.argument("path", type=click.Path(exists=True), required=False)
@click.option("--command", type=click.Choice(local_server_commands.keys()))
@click.option("--config-path", type=click.Path())
@click.option(
    "--use-frontend-server",
    type=str,
    help="Connect to frontend dev server at specified host (e.g. http://localhost:3000)",
)
def main(path: str, command: str, config_path: str, use_frontend_server: str):
    if config_path:
        desktop_app.set_user_settings_path(Path(config_path))

    # Load configs and repo path
    user_config = desktop_app.get_user_settings()

    if path:
        repo_path = Path(path)
    else:
        repo_path = Path(user_config.repository_path)
    log.info("Using repository: %s" % repo_path)

    repo_path_str = str(repo_path)
    user_config.repository_path = repo_path_str

    repo_settings = desktop_app.get_repo_settings(repo_path)

    # Check if another instance is running and/or start the local server
    # When using frontend server, we might not need to check for other instances
    local_server = DesktopServer(
        commands=local_server_commands,
        media_store_path=repo_settings.media_store_path,
    )

    if (
        not use_frontend_server
    ):  # Only check for other instances when using local server
        if local_server.another_instance_is_running():
            port = local_server.get_port_from_lock_file()
            if command:
                DesktopServer.send_command(port, command)
            else:
                DesktopServer.send_command(port, "raise_window")
            return

    # Start the local server (needed for API endpoints even when using frontend server)
    local_server.start()

    app = DesktopApp()
    app.aboutToQuit.connect(local_server.stop)

    configure_for_qt(app)

    # If there's changes after the load it means that some default is not saved
    # to disk or some other irregularity has been handled by the config class
    if user_config.changes_present:
        desktop_app.save_user_settings(user_config)

    # Temporary restore logic for testing migrations
    mock_repo_path = "/sync/projects/misli/mock_repo"
    mock_repo_backup_path = "/sync/projects/misli/mock_repo_backup"
    if str(repo_path) == mock_repo_path:
        import shutil

        if os.path.exists(mock_repo_backup_path):
            log.info(f"Restoring mock repo from backup for migration testing")
            if os.path.exists(mock_repo_path):
                shutil.rmtree(mock_repo_path)
            shutil.copytree(mock_repo_backup_path, mock_repo_path)
            log.info(f"Mock repo restored from {mock_repo_backup_path}")

    # Init the repo (run migrations via ProjectFolderManager)
    pfm = ProjectFolderManager(repo_path)
    pamet.set_project_folder_manager(pfm)

    if os.path.exists(repo_path):
        # index_folder detects legacy files and runs migrations if needed
        pfm.index_folder()

        # Create the main repo instance (now loads V5 files post-migration)
        fs_repo = FSStorageRepository.open(repo_path, queue_save_on_change=True)
        fs_repo.load_all_pages()
    else:
        fs_repo = FSStorageRepository.new(repo_path, queue_save_on_change=True)

    # Initialize media backend service and register globally (after PFM is set)
    media_backend = MediaStorageBackendService(
        repo_settings.media_store_path, project_manager=pfm
    )
    pamet.set_media_backend_service(media_backend)
    local_server.register_media_routes(media_backend)

    if repo_settings.changes_present():
        desktop_app.save_repo_settings(repo_settings)

    pamet.set_sync_repo(fs_repo)
    desktop_app.set_media_store(MediaStore(repo_settings.media_store_path))

    pamet.set_undo_service(UndoService(pamet_channels.entity_change_sets_per_TLA))

    # Determine the endpoint URL based on frontend server option
    desktop_api_base_url = f"http://localhost:{local_server.port}"
    if use_frontend_server:
        # Use the provided frontend server URL
        endpoint_url = use_frontend_server
        print(f"Using frontend dev server at {endpoint_url}")
    else:
        # Use the local server
        endpoint_url = desktop_api_base_url
        print(f"Using local server at {endpoint_url}")

    # # Debug
    # misli_channels.state_changes_per_TLA_by_id.subscribe(
    #     lambda x: print(f'STATE_CHANGES_BY_ID CHANNEL: {x}'))

    # Create WebShellWindow - show dev tools when using frontend server
    web_shell = WebShellWindow(
        endpoint=endpoint_url,
        desktop_api_base_url=desktop_api_base_url,
        show_dev_tools=bool(use_frontend_server),
    )
    web_shell.showMaximized()

    # Start watching the project folder for changes
    try:
        pamet.project_folder_manager().start_watching()
        app.aboutToQuit.connect(lambda: pamet.project_folder_manager().stop_watching())
    except Exception as e:
        log.error(f"Failed to start project folder watcher: {e}")

    # search_service = FuzzySearchService(
    #     pamet_channels.entity_change_sets_per_TLA)
    # search_service.load_all_content()
    # pamet.set_search_service(search_service)

    # other_page_list_service = OtherPagesListUpdateService()
    # other_page_list_service.start()

    # Setup exception reporting for failed actions
    if LOGGING_LEVEL != LoggingLevels.DEBUG.value:

        def show_exception_for_failed_action(action_call: ActionCall):
            if action_call.run_state != ActionRunStates.FAILED:
                return
            title = f'Exception raised during action "{action_call.name}"'
            app.present_exception(exception=action_call.error, title=title)

        # actions_log_channel.subscribe(show_exception_for_failed_action)

    if repo_settings.backups_enabled:
        backup_service = FSStorageBackupService(
            backup_folder=repo_settings.backup_folder,
            repository=fs_repo,
            changeset_channel=pamet_channels.entity_change_sets_per_TLA,
            record_all_changes=repo_settings.record_all_changes,
        )

        service_started = False
        try:
            backup_service.start()
            service_started = True
        except AnotherServiceAlreadyRunningException:
            log.info(
                "Backup service not started. " "Probably another instance is running"
            )
            reply = QMessageBox.question(
                web_shell,
                "Backup service conflict",
                "A backup service lock is present. If you're sure there's "
                "no other instances running on the same repo - "
                "press Yes to override.",
            )
            if reply == QMessageBox.StandardButton.Yes:
                backup_service.service_lock_path().unlink()
                backup_service.start()
                service_started = True

        if service_started:
            app.aboutToQuit.connect(backup_service.stop)
            pamet.desktop_app.set_backup_service(backup_service)

    # # Experimental semantic search
    # if repo_settings.semantic_search_enabled:
    #     from pamet.services.search.semantic import SemanticSearchService
    #     semantic_search_service = SemanticSearchService(
    #         data_folder=repo_path / '__semantic_index__',
    #         change_set_channel=pamet_channels.entity_change_sets_per_TLA)

    #     print('Loading semantic search index...')
    #     semantic_search_service.load_all_content()
    #     print('Semantic search index loaded')
    #     set_semantic_search_service(semantic_search_service)

    fusion.set_main_loop_exception_handler(
        lambda e: app.present_exception(e, title="Main loop exception")
    )

    return app.exec()


if __name__ == "__main__":
    main()
