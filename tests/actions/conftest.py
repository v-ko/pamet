from PySide6.QtCore import Qt
import pytest
import fusion

import pamet
from pamet.desktop_app.helpers import configure_for_qt
from pamet.desktop_app.app import DesktopApp
from pamet.services.search.fuzzy import FuzzySearchService
from pamet.services.undo import UndoService
from pamet.views.window.widget import WindowWidget
from pamet.actions import window as window_actions
from pamet.actions import other as other_actions
from pamet import channels as pamet_channels


def pytest_addoption(parser):
    parser.addoption(
        '--headless',
        # action='store',
        default=False,
        type=bool,
        help='Whether to show the app when running the action tests')


@pytest.fixture
def window_fixture(request):
    run_headless = request.config.getoption('--headless')
    # Init the app
    fusion.gui.set_reproducible_ids(True)
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
