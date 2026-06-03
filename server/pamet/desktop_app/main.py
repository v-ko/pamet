import logging
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import cast

import click
import sivkit
from PySide6.QtCore import QStandardPaths
from sivkit.util import deep_merge
from slugify import slugify

from pamet.constants import LOCAL_USER_ID
from pamet.desktop_app.config import (
    PAMET_APP_DATA_DIR,
    PAMET_CONFIG_DIR,
    web_app_static_build_path,
)
from pamet.model.config import ScriptSettings, UserSettings, default_script_settings
from pamet.services.config_file_manager import load_user_settings, save_user_settings
from pamet.services.rest_api.client import send_command
from pamet.services.rest_api.instance_check import get_running_instance_port
from pamet.services.rest_api.routes.desktop import PUBLIC_COMMAND_NAMES
from pamet.storage.migrations.v4_to_v5 import (
    archive_v4_user_settings,
    process_v4_user_settings,
)

log = sivkit.get_logger(__name__)


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
@click.option(
    "--mock-v4-fixture",
    is_flag=True,
    default=False,
    help="Rebuild the v4 mock-repo fixture and run against isolated config/app-data dirs.",
)
def main(
    project_path: Path | None,
    command: str,
    use_frontend_server: str | None,
    mock_v4_fixture: bool,
):
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # CLI flag is just an alias for the env var; flag wins if both are set.
    frontend_dev_server = use_frontend_server or os.environ.get(
        "PAMET_FRONTEND_DEV_SERVER"
    )

    # Check if another instance is running (must happen before prepare.py
    # which wipes the config dir and would remove the lock file)
    port = get_running_instance_port(PAMET_CONFIG_DIR)
    if port:
        log.info(
            f"Another instance is already running on port {port} — sending command and exiting"
        )
        if command:
            send_command(port, command)
        else:
            send_command(port, "raise_window")
        return

    # Temporary fixture setup for migration testing. When --mock-v4-fixture is
    # passed, rebuild the prepared fixture on startup so legacy user settings
    # can be restored from it into isolated app-data. Guarded to refuse running
    # against the user's real Qt-default config/app-data dirs.
    if mock_v4_fixture:
        prepared_repo_dir = (
            Path(__file__).resolve().parents[2] / "tests" / "mock_v4_project"
        )
        prepare_script_path = prepared_repo_dir / "prepare.py"

        qt_default_config = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
        qt_default_app_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        if PAMET_CONFIG_DIR == qt_default_config:
            raise Exception(
                f"--mock-v4-fixture refuses to run on default config dir: {PAMET_CONFIG_DIR}"
            )
        if PAMET_APP_DATA_DIR == qt_default_app_data:
            raise Exception(
                f"--mock-v4-fixture refuses to run on default app-data dir: {PAMET_APP_DATA_DIR}"
            )

        log.info("Preparing mock repo and settings via %s", prepare_script_path)
        subprocess.run(
            [sys.executable, str(prepare_script_path)],
            cwd=prepared_repo_dir,
            check=True,
        )
    # END OF TMP MIGRATION TESTING LOGIC

    # Load v5 UserSettings, migrating from v4 if needed. The v4 ``settings.json``
    # lives in the Qt GenericDataLocation dir (PAMET_APP_DATA_DIR), e.g.
    # ``~/.local/share/pamet/settings.json`` on Linux. After consumption it is
    # archived as a sibling .v4.bak.
    legacy_settings_path = PAMET_APP_DATA_DIR / "settings.json"
    had_legacy_settings = legacy_settings_path.exists()
    legacy_overrides: dict = {}
    try:
        legacy_overrides = process_v4_user_settings(PAMET_APP_DATA_DIR) or {}
    except Exception as e:
        log.error("Failed to migrate legacy user settings: %s", e)

    settings = load_user_settings()

    if had_legacy_settings and settings is not None:
        log.warning(
            "Legacy v4 user settings found but current settings already exist "
            "— ignoring legacy values"
        )
        legacy_overrides = {}

    if settings is None:
        log.info("No user settings found — creating defaults")
        # Start from v5 defaults, then overlay any v4-derived overrides.
        script_settings: ScriptSettings = default_script_settings()
        scripts_overrides = legacy_overrides.get("scripts")
        if scripts_overrides:
            script_settings = cast(
                ScriptSettings,
                deep_merge(script_settings, scripts_overrides),
            )
        settings = UserSettings(
            id="user-settings",
            userId=LOCAL_USER_ID,
            userName="Local User",
            projects=[],
            scripts=script_settings,
        )
        save_user_settings(settings)

    if had_legacy_settings:
        archive_v4_user_settings(legacy_settings_path)

    legacy_repo_path = legacy_overrides.get("repository_path")

    # Setup project if legacy present or path is passed via cli argument
    project_id: str | None = None
    project_title: str | None = None

    # If v4 settings had a repo path - use it for project startup
    if not project_path and legacy_repo_path:
        if not Path(legacy_repo_path).exists():
            log.error(
                "Legacy repository_path %s does not exist. Ignoring.", legacy_repo_path
            )
        else:
            project_path = Path(legacy_repo_path).resolve()
            project_title = project_path.name
            project_id = slugify(project_title)

    elif project_path is not None:
        # Resolve so folder-name derivation works for relative inputs like "."
        # (Path(".").stem == "", which silently broke project_id/title).
        project_path = project_path.resolve()

        # If project is already tracked - use the existing title/id
        for tracked_project in settings.projects or []:
            if tracked_project.get("uri") == project_path.as_uri():
                project_id = tracked_project.get("id")
                project_title = tracked_project.get("title")
                break

        # If not tracked - set default id and title based on folder name
        if not project_title:
            project_title = project_path.name

        if not project_id:
            project_id = slugify(project_title)

        if not project_title or not project_id:
            raise RuntimeError(
                f"Could not derive a project id/title from path {project_path}"
            )

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

    # Silence noisy third-party loggers while keeping our own level low.
    logging.getLogger("peewee").setLevel(logging.WARNING)

    # ── Heavy imports (PySide6, Qt, etc.) deferred to here ───────────
    from PySide6.QtCore import QTimer
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle
    from PySide6.QtWebEngineQuick import QtWebEngineQuick
    from sivkit.platform.qt_widgets.qt_main_loop import QtMainLoop

    import pamet
    import pamet.commands  # noqa: F401 — triggers @command registrations
    from pamet import desktop_app
    from pamet.actions.app import open_tab
    from pamet.desktop_app.app import DesktopApp
    from pamet.desktop_app.init_config import setup_fonts_and_icons
    from pamet.services.desktop_storage_service import DesktopStorageService
    from pamet.services.rest_api.desktop_server import DesktopServer
    from pamet.views.app_window.qml_backend import (
        QmlAppBackend,
        TitleBarDoubleClickFilter,
    )
    from pamet.views.app_window.view_state import AppWindowViewState

    # The desktop server always serves the JSON API. It also serves the SPA
    # bundle UNLESS a frontend dev server is configured — in which case the
    # WebEngineView loads the dev server URL directly and the SPA discovers
    # the API base URL via window.PAMET_DESKTOP_API_BASE_URL (injected by the
    # WebEngineProfile). This mirrors the production deployment, where SPA
    # and API live on different hosts (e.g. app.pamet.io / api.pamet.io).
    if frontend_dev_server:
        static_build_path = None
        log.info("Frontend will be served via dev server: %s", frontend_dev_server)
    else:
        static_build_path = web_app_static_build_path()
        log.info("Serving bundled web-app build from %s", static_build_path)

    local_server = DesktopServer(
        config_dir=PAMET_CONFIG_DIR,
        web_app_static_build_path=static_build_path,
        frontend_dev_server_url=frontend_dev_server,
    )
    local_server.start()

    # Workaround for Qt bug: QML WebEngineView renders black/stale after
    # minimize-restore with OpenGL and transparent with Vulkan RHI backends.
    # Software rendering is unaffected.
    # https://qt-project.atlassian.net/browse/PYSIDE-3323
    if not os.environ.get("QT_QUICK_BACKEND"):
        os.environ["QT_QUICK_BACKEND"] = "software"
        log.info(
            "Forcing software QML backend (WebEngineView minimize-restore workaround)"
        )

    # QtWebEngineQuick must be initialized before the QApplication
    QtWebEngineQuick.initialize()

    app = DesktopApp()
    app.aboutToQuit.connect(local_server.stop)

    log.info("Using config folder: %s", PAMET_CONFIG_DIR)
    log.info("Using app data folder: %s", PAMET_APP_DATA_DIR)
    desktop_app.set_app(app)
    sivkit.set_main_loop(QtMainLoop(app))
    setup_fonts_and_icons()

    desktop_storage_service = DesktopStorageService()
    pamet.set_desktop_storage_service(desktop_storage_service)

    desktop_api_base_url = f"http://localhost:{local_server.port}"
    frontend_base_url = (
        frontend_dev_server.rstrip("/") if frontend_dev_server else desktop_api_base_url
    )
    if project_id is None:
        initial_project_url = frontend_base_url
    else:
        initial_project_url = f"{frontend_base_url}/{LOCAL_USER_ID}/{project_id}"

    # Create the QML app window

    QQuickStyle.setStyle("Fusion")

    view_state = AppWindowViewState()
    qml_backend = QmlAppBackend(
        view_state=view_state,
        endpoint=initial_project_url,
        desktop_api_base_url=desktop_api_base_url,
    )

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appState", view_state)
    engine.rootContext().setContextProperty("backend", qml_backend)

    qml_path = (
        Path(__file__).resolve().parents[1] / "views" / "app_window" / "AppWindow.qml"
    )
    engine.load(qml_path)

    if not engine.rootObjects():
        print("Failed to load QML")
        return 1

    # Install a native event filter for title-bar double-click → maximize
    window = engine.rootObjects()[0]
    title_bar_height = 42  # must match header height in AppWindow.qml
    dbl_filter = TitleBarDoubleClickFilter(window, title_bar_height)
    window.installEventFilter(dbl_filter)

    # Open the initial tab deferred so QML Repeater bindings are wired
    QTimer.singleShot(0, lambda: open_tab(view_state, initial_project_url, True))

    sivkit.set_main_loop_exception_handler(
        lambda e: app.present_exception(e, title="Main loop exception")
    )

    return app.exec()


if __name__ == "__main__":
    main()
