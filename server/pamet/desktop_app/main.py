import json
import signal
import subprocess
import sys
from pathlib import Path

import click
import fusion
from fusion.libs.action.action_call import ActionCall, ActionRunStates
from fusion.logging import LOGGING_LEVEL, LoggingLevels
from slugify import slugify

import pamet
from pamet import desktop_app

# from fusion import actions_log_channel
from pamet.constants import DEFAULT_PROJECT_ID, DEFAULT_PROJECT_TITLE, LOCAL_USER_ID
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.config import (
    APP_DATA_DIR,
    CONFIG_DIR,
    USER_SETTINGS_DIR,
    repo_settings_path,
)
from pamet.desktop_app.init_config import configure_for_qt
from pamet.desktop_app.screen_snippet import grab_screen_snippet
from pamet.desktop_app.web_shell import WebShellWindow
from pamet.model.config import UserSettings
from pamet.services.config_file_manager import load_user_settings, save_user_settings
from pamet.services.desktop_storage_service import DesktopStorageService
from pamet.services.rest_api.desktop import DesktopServer

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
@click.argument(
    "project_path",
    type=click.Path(
        exists=True, dir_okay=True, file_okay=False, readable=True, path_type=Path
    ),
    required=False,
)
@click.option("--command", type=click.Choice(local_server_commands.keys()))
@click.option(
    "--use-frontend-server",
    type=str,
    help="Connect to frontend dev server at specified host (e.g. http://localhost:3000)",
)
def main(project_path: Path | None, command: str, use_frontend_server: str):
    signal.signal(signal.SIGINT, signal.SIG_DFL)

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

    if CONFIG_DIR != expected_config_dir:
        raise Exception(f"Running non-mock config: {CONFIG_DIR}")
    if APP_DATA_DIR != expected_app_data_dir:
        raise Exception(f"Running non-mock app data: {APP_DATA_DIR}")
    if project_path and Path(project_path) != prepared_repo_path:
        raise Exception(f"Running non-mock repo: {project_path}")

    log.info("Preparing mock repo and settings via %s", prepare_script_path)
    subprocess.run(
        [sys.executable, str(prepare_script_path)],
        cwd=prepared_repo_dir,
        check=True,
    )
    # END OF TMP MIGRATION TESTING LOGIC

    # Setup initial user settings if not present
    settings = load_user_settings()
    if settings is None:
        log.info("No user settings found — creating defaults")
        settings = UserSettings(
            id="user-settings",
            userId=LOCAL_USER_ID,
            userName="Local User",
            projects=[],
        )
        save_user_settings(settings)

    # Setup project if legacy present or path is passed via cli argument
    project_id: str | None = None
    project_title: str | None = None

    # If v4 settings exist - extract repo path for project startup
    legacy_settings_path = APP_DATA_DIR / "settings.json"
    if not project_path and legacy_settings_path.exists():
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
            project_path = Path(legacy_repo_path)
            # It was the default project so set the default name/id
            project_id = DEFAULT_PROJECT_ID
            project_title = DEFAULT_PROJECT_TITLE

    elif project_path is not None:
        # If project is already tracked - use the existing title/id
        for tracked_project in settings.projects or []:
            if tracked_project.get("uri") == project_path.resolve().as_uri():
                project_id = tracked_project.get("id")
                project_title = tracked_project.get("title")
                break

        # If not tracked - set default id and title based on folder name
        if not project_title:
            project_title = project_path.stem

        if not project_id:
            project_id = slugify(project_title)

    # If the path is set (regardless if legacy or cli) - we need to add it to the tracked projects
    # so that the frontend can load it
    if project_path and project_title and project_id:
        log.info("Start up repository: %s" % project_path)

        if not repo_settings_path(project_path).exists():
            log.info(f"No repo settings found in {project_path} — creating settings.")

        # Upsert tracked project in user settings
        project_data = {
            "id": project_id,
            "uri": project_path.resolve().as_uri(),
            "title": project_title,
        }
        projects = list(settings.projects or [])
        replaced = False
        for i, p in enumerate(projects):
            if p.get("id") == project_id:
                projects[i] = project_data
                replaced = True
                break
        if not replaced:
            projects.append(project_data)
        settings.projects = projects
        save_user_settings(settings)

    # Check if another instance is running and/or start the local server
    # When using frontend server, we might not need to check for other instances
    local_server = DesktopServer(
        commands=local_server_commands,
        config_dir=CONFIG_DIR,
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

    if project_id is None:
        initial_project_url = endpoint_url.rstrip("/")
    else:
        initial_project_url = f"{endpoint_url.rstrip('/')}/{LOCAL_USER_ID}/{project_id}"

    # # Debug
    # misli_channels.state_changes_per_TLA_by_id.subscribe(
    #     lambda x: print(f'STATE_CHANGES_BY_ID CHANNEL: {x}'))

    # Create WebShellWindow - show dev tools when using frontend server
    web_shell = WebShellWindow(
        endpoint=initial_project_url,
        desktop_api_base_url=desktop_api_base_url,
        webengine_profile_root=USER_SETTINGS_DIR / "webengine-profile",
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
