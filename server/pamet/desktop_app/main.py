import signal
import subprocess
import sys
from pathlib import Path

import click
import fusion
from fusion.platform.qt_widgets.qt_main_loop import QtMainLoop
from slugify import slugify

import pamet
import pamet.commands  # noqa: F401 — triggers @command registrations
from pamet import desktop_app
from pamet.constants import DEFAULT_PROJECT_ID, DEFAULT_PROJECT_TITLE, LOCAL_USER_ID
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.config import APP_DATA_DIR, CONFIG_DIR, USER_SETTINGS_DIR
from pamet.desktop_app.init_config import setup_fonts_and_icons
from pamet.model.config import UserSettings
from pamet.services.config_file_manager import load_user_settings, save_user_settings
from pamet.services.desktop_storage_service import DesktopStorageService
from pamet.services.rest_api.client import send_command
from pamet.services.rest_api.desktop_server import DesktopServer
from pamet.services.rest_api.instance_check import get_running_instance_port
from pamet.services.rest_api.routes.desktop import PUBLIC_COMMAND_NAMES
from pamet.storage.migrations.v4_to_v5 import migrate_v4_user_settings
from pamet.views.app_window.app_window import AppWindow

log = fusion.get_logger(__name__)


@click.command()
@click.argument(
    "project_path",
    type=click.Path(
        exists=True, dir_okay=True, file_okay=False, readable=True, path_type=Path
    ),
    required=False,
)
@click.option("--command", type=click.Choice(sorted(PUBLIC_COMMAND_NAMES)))
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

    # Migrate legacy v4 user settings if present
    legacy_settings_data = None
    legacy_settings_path = APP_DATA_DIR / "settings.json"
    try:
        legacy_settings_data = migrate_v4_user_settings(APP_DATA_DIR)
    except Exception as e:
        log.error("Failed to migrate legacy user settings: %s", e)

    settings = load_user_settings()

    if legacy_settings_data is not None:
        if settings is not None:
            log.warning(
                "Legacy v4 user settings found but current settings already exist "
                "— ignoring legacy values"
            )
        legacy_settings_path.unlink()
        log.info("Deleted legacy user settings file %s", legacy_settings_path)

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

    # If v4 settings had a repo path - use it for project startup
    if (
        not project_path
        and legacy_settings_data
        and legacy_settings_data.get("repository_path")
    ):
        legacy_repo_path = legacy_settings_data["repository_path"]
        if not Path(legacy_repo_path).exists():
            log.error(
                "Legacy repository_path %s does not exist. Ignoring.", legacy_repo_path
            )
        else:
            project_path = Path(legacy_repo_path)
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

    # Check if another instance is running
    if not use_frontend_server:
        port = get_running_instance_port(CONFIG_DIR)
        if port:
            if command:
                send_command(port, command)
            else:
                send_command(port, "raise_window")
            return

    # Start the local server (needed for API endpoints even when using frontend server)
    local_server = DesktopServer(config_dir=CONFIG_DIR)
    local_server.start()

    app = DesktopApp()
    app.aboutToQuit.connect(local_server.stop)

    log.info("Using config folder: %s", CONFIG_DIR)
    log.info("Using app data folder: %s", APP_DATA_DIR)
    desktop_app.set_app(app)
    fusion.set_main_loop(QtMainLoop(app))
    setup_fonts_and_icons()

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

    # Create the app window - show dev tools when using frontend server
    app_window = AppWindow(
        endpoint=initial_project_url,
        desktop_api_base_url=desktop_api_base_url,
        webengine_profile_root=USER_SETTINGS_DIR / "webengine-profile",
        show_dev_tools=bool(use_frontend_server),
    )
    app_window.showMaximized()

    fusion.set_main_loop_exception_handler(
        lambda e: app.present_exception(e, title="Main loop exception")
    )

    return app.exec()


if __name__ == "__main__":
    main()
