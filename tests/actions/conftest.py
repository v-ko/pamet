from PySide6.QtCore import Qt
import pytest
import fusion
from fusion.libs import entity as entity_lib
from fusion.libs import channel as channel_lib
# from fusion.state_manager import FusionStateManager

import pamet
from pamet.desktop_app.util import configure_for_qt
from pamet.desktop_app.app import DesktopApp
from pamet.services.search.fuzzy import FuzzySearchService
from pamet.services.undo import UndoService
from pamet.storage.file_system.repository import FSStorageRepository
from pamet.views.window.widget import WindowWidget
from pamet.actions import window as window_actions
from pamet.actions import other as other_actions
from pamet import channels as pamet_channels


def pytest_addoption(parser):
    parser.addoption(
        '--headless',
        action='store',
        default=False,
        type=bool,
        help='Whether to show the app when running the action tests')


@pytest.fixture
def window_fixture(request, tmp_path):
    run_headless = request.config.getoption('--headless')
    # Init the app
    fusion.set_reproducible_ids(True)
    entity_lib.reset_entity_id_counter()
    channel_lib.unsibscribe_all()  # TODO: there should be a cleaner way
    fusion.fsm.reset()
    pamet.reset()

    fs_repo = FSStorageRepository.new(tmp_path, queue_save_on_change=True)
    pamet.set_sync_repo(fs_repo)

    app = DesktopApp()
    configure_for_qt(app)

    # Setup services
    pamet.set_undo_service(
        UndoService(pamet_channels.entity_change_sets_per_TLA))

    search_service = FuzzySearchService(
        pamet_channels.entity_change_sets_per_TLA)
    search_service.load_all_content()
    pamet.set_search_service(search_service)

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
