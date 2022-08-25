from .logging import get_logger
from misli.entity_library import entity_type
from misli.entity_library.entity import Entity
from misli.entity_library.change import Change, ChangeTypes
from .pubsub import set_main_loop, main_loop, call_delayed
from .pubsub import SubscriptionTypes, Subscription, Channel
from . import gui


line_spacing_in_pixels = 20


def configure_for_qt(app):
    from misli.gui.utils.qt_widgets.qt_main_loop import QtMainLoop
    from misli.gui.utils.qt_widgets.provider import QtWidgetsUtilProvider
    from misli.gui.views.context_menu.widget import ContextMenuWidget
    from misli.gui.views.input_modal.widget import InputDialogWidget
    from misli.gui.views.message_box.widget import MessageBoxWidget

    set_main_loop(QtMainLoop(app))
