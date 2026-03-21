import json
import subprocess
import sys
from pathlib import Path

import click
from fusion.libs.action.action_call import ActionCall, ActionRunStates
from fusion.logging import LOGGING_LEVEL, LoggingLevels

# from fusion import actions_log_channel
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.config import get_repo_settings, repo_settings_path
from pamet.desktop_app.init_config import configure_for_qt
from pamet.desktop_app.screen_snippet import grab_screen_snippet
from pamet.desktop_app.web_shell import WebShellWindow
from pamet.services.desktop_storage_service import DesktopStorageService
from pamet.services.media_store import MediaStore
from pamet.services.rest_api.desktop import DesktopServer
from pamet.services.undo import UndoService

import fusion
import pamet
from pamet import channels as pamet_channels
from pamet import desktop_app

log = fusion.get_logger(__name__)
LOCAL_USER_ID = "local"


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
@click.option(
    "--use-frontend-server",
    type=str,
    help="Connect to frontend dev server at specified host (e.g. http://localhost:3000)",
)
def main(path: str, command: str, use_frontend_server: str):
    # Temporary fixture setup for migration testing. Rebuild the prepared fixture
    # on startup, then restore legacy user settings from it into isolated app-data.
    prepared_repo_dir = (
        Path(__file__).resolve().parents[2] / "tests" / "mock_v4_project"
    )
    prepare_script_path = prepared_repo_dir / "prepare.py"

    prepared_fixture_path = prepared_repo_dir / "prepared_test_time"
    prepared_repo_path = prepared_fixture_path / "repo"
    expected_config_dir = prepared_fixture_path / "config"
    expected_app_data_dir = prepared_fixture_path / "app_data"

    if desktop_app.CONFIG_DIR != expected_config_dir:
        raise Exception(f"Running non-mock config: {desktop_app.CONFIG_DIR}")
    if desktop_app.APP_DATA_DIR != expected_app_data_dir:
        raise Exception(f"Running non-mock app data: {desktop_app.APP_DATA_DIR}")
    if path and Path(path) != prepared_repo_path:
        raise Exception(f"Running non-mock repo: {path}")

    log.info("Preparing mock repo and settings via %s", prepare_script_path)
    subprocess.run(
        [sys.executable, str(prepare_script_path)],
        cwd=prepared_repo_dir,
        check=True,
    )
    # END OF TMP MIGRATION TESTING LOGIC

    # Setup initial user settings if not present
    if not desktop_app.user_settings_path().exists():
        desktop_app.save_user_settings(
            {
                "id": LOCAL_USER_ID,
                "name": "Local User",
                "projects": [],
            }
        )

    # If v4 settings exist - extract repo path for project startup
    legacy_settings_path = desktop_app.APP_DATA_DIR / "settings.json"
    if not path and legacy_settings_path.exists():
        log.info("Reading legacy settings from %s", legacy_settings_path)
        try:
            legacy_settings = json.loads(legacy_settings_path.read_text())
        except Exception as e:
            log.error("Failed to read legacy settings: %s", e)
            legacy_settings = {}

        legacy_repo_path = legacy_settings.get("repository_path")
        if not legacy_repo_path:
            log.warning("No repository_path in legacy settings. Starting without repo.")
        elif not Path(legacy_repo_path).exists():
            log.error(
                "Legacy repository_path %s does not exist. Ignoring.", legacy_repo_path
            )
        else:
            path = str(legacy_repo_path)

    # If the path is set (regardless if legacy or cli) - we need to add it to the tracked projects
    # so that the frontend can load it
    initial_project_id: str | None = None
    repo_path: Path | None = Path(path) if path else None
    media_store_path = desktop_app.APP_DATA_DIR / "media"

    if repo_path is not None:
        log.info("Start up repository: %s" % repo_path)

        if not repo_settings_path(repo_path).exists():
            log.info(f"No repo settings found in {repo_path} — creating settings.")
            desktop_app.upsert_tracked_project(
                project_id="notebook",
                uri=repo_path.resolve().as_uri(),
                user_id=LOCAL_USER_ID,
                title="Notebook",
            )

    # Check if another instance is running and/or start the local server
    # When using frontend server, we might not need to check for other instances
    local_server = DesktopServer(
        commands=local_server_commands,
        media_store_path=media_store_path,
        config_dir=desktop_app.CONFIG_DIR,
    )

    if (
        not use_frontend_server
    ):  # Only check for other instances when using local server
        port = local_server.get_running_instance_port()
        if port:
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

    desktop_storage_service = DesktopStorageService()
    pamet.set_desktop_storage_service(desktop_storage_service)

    desktop_app.set_media_store(MediaStore(media_store_path))

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

    if initial_project_id is None:
        initial_project_url = endpoint_url.rstrip("/")
    else:
        initial_project_url = (
            f"{endpoint_url.rstrip('/')}/{LOCAL_USER_ID}/{initial_project_id}"
        )

    # # Debug
    # misli_channels.state_changes_per_TLA_by_id.subscribe(
    #     lambda x: print(f'STATE_CHANGES_BY_ID CHANNEL: {x}'))

    # Create WebShellWindow - show dev tools when using frontend server
    web_shell = WebShellWindow(
        endpoint=initial_project_url,
        desktop_api_base_url=desktop_api_base_url,
        webengine_profile_root=desktop_app.user_settings_path().parent
        / "webengine-profile",
        show_dev_tools=bool(use_frontend_server),
    )
    web_shell.showMaximized()

    # Setup exception reporting for failed actions
    if LOGGING_LEVEL != LoggingLevels.DEBUG.value:

        def show_exception_for_failed_action(action_call: ActionCall):
            if action_call.run_state != ActionRunStates.FAILED:
                return
            title = f'Exception raised during action "{action_call.name}"'
            app.present_exception(exception=action_call.error, title=title)

        # actions_log_channel.subscribe(show_exception_for_failed_action)

    fusion.set_main_loop_exception_handler(
        lambda e: app.present_exception(e, title="Main loop exception")
    )

    return app.exec()


if __name__ == "__main__":
    main()
