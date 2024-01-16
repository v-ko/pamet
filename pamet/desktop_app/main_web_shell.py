from pathlib import Path
import click
import fusion
from fusion.logging import LOGGING_LEVEL, LoggingLevels

from pamet import commands, desktop_app
import pamet
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.web_shell import WebShellWindow
from pamet.services.media_store import MediaStore
from pamet.services.rest_api.desktop import DesktopServer
from pamet.storage.file_system.repository import FSStorageRepository

log = fusion.get_logger(__name__)


def raise_a_window():
    windows = [
        w for w in DesktopApp.instance().topLevelWidgets()
        if isinstance(w, WebShellWindow)
    ]
    if windows:
        windows[0].show()
        windows[0].activateWindow()
        windows[0].raise_()


local_server_commands = {
    # 'grab_screen_snippet': commands.grab_screen_snippet,
    # 'raise_window': raise_a_window
}


@click.command()
@click.argument('path', type=click.Path(exists=True), required=False)
@click.option('--command', type=click.Choice(local_server_commands.keys()))
@click.option('--config-path', type=click.Path())
@click.option('--web-build-dir', type=click.Path())
def main(path: str, command: str, config_path: str, web_build_dir: str):
    # Check if another instance is running and/or start the local server
    debugging = bool(LOGGING_LEVEL == LoggingLevels.DEBUG.value)
    if debugging:
        port = 3333
        print(f'Debugging mode. Setting desktop server port to {port}')
    else:
        port = DesktopServer.DEFAULT_PORT

    repo_path = Path(path)
    log.info('Using repository: %s' % repo_path)

    if repo_path.exists():
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

    local_server = DesktopServer(
        media_store_path=repo_settings.media_store_path,
        port=port,
        # commands=local_server_commands,
        web_app_static_build_path=web_build_dir,
        # web_app_debug_server_host='http://localhost',
    )

    pamet.set_sync_repo(fs_repo)
    desktop_app.set_media_store(MediaStore(repo_settings.media_store_path))

    # if local_server.another_instance_is_running() and not debugging:
    #     port = local_server.get_port_from_lock_file()
    #     if command:
    #         DesktopServer.send_command(port, command)
    #     else:
    #         DesktopServer.send_command(port, 'raise_window')
    #     return
    # else:
        # local_server.start()

    local_server.start()

    app = DesktopApp()
    app.aboutToQuit.connect(local_server.stop)

    web_shell = WebShellWindow(
        endpoint=f'http://localhost:{local_server.port}')

    web_shell.show()
    app.exec()


if __name__ == '__main__':
    main()
