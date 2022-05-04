import signal
import misli
from misli.gui.actions_library import action

from pamet.desktop_app.app import DesktopApp
from pamet.views.window.widget import WindowWidget

signal.signal(signal.SIGINT, signal.SIG_DFL)

log = misli.get_logger(__name__)


@log.traced
@action('change_window_title')
def change_window_title(window_state, new_title: str):
    window_state.title = new_title
    misli.gui.update_state(window_state)


@log.traced
def main():
    misli.configure_for_qt()

    desktop_app = DesktopApp()
    window = WindowWidget(title='Initial title')
    window.showMaximized()
    misli.call_delayed(change_window_title,
                       2,
                       kwargs=dict(window_state=window.state,
                                   new_title='It works bchz'))
    return desktop_app.exec()


if __name__ == '__main__':
    main()
