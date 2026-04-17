import fusion
import pytest
from fusion.libs import channel as channel_lib, model as entity_lib
from PySide6.QtCore import Qt

import pamet
from pamet.actions import window as window_actions
from pamet.desktop_app.app import DesktopApp
from pamet.desktop_app.init_config import configure_for_qt
from pamet.storage.file_system.repository import FSStorageRepository


def pytest_addoption(parser):
    parser.addoption(
        "--headless",
        action="store",
        default=False,
        type=bool,
        help="Whether to show the app when running the action tests",
    )


@pytest.fixture
def window_fixture(request, tmp_path):
    """DEPRECATED
    can be helpful when fixing the new web shell for testing"""
    run_headless = request.config.getoption("--headless")
    # Init the app
    fusion.set_reproducible_ids(True)
    entity_lib.reset_entity_id_counter()
    channel_lib.unsibscribe_all()  # TODO: there should be a cleaner way
    fusion.fsm.reset()
    pamet.reset()

    fs_repo = FSStorageRepository.new(tmp_path, queue_save_on_change=True)
    # pamet.set_sync_repo(fs_repo)

    app = DesktopApp()
    configure_for_qt(app)

    # Create an initial page and open the window
    start_page = other_actions.create_default_page()
    window_state = window_actions.new_browser_window()
    window = WindowWidget(initial_state=window_state)
    if run_headless:
        window.setAttribute(Qt.WA_DontShowOnScreen)

    window_actions.new_browser_tab(window_state, start_page)
    window.showMaximized()
    fusion.main_loop().process_events()

    yield window
    app.shutdown()
