from .logging import get_logger
from misli.entity_library import entity_type
from misli.entity_library.entity import Entity
from misli.entity_library.change import Change, ChangeTypes
from .pubsub import *
from . import gui


def configure_for_qt():
    from misli.gui.utils.qt_widgets.qt_main_loop import QtMainLoop
    from misli.gui.utils.qt_widgets.provider import QtWidgetsUtilProvider
    from misli.gui.views.context_menu.widget import ContextMenuWidget
    from misli.gui.views.input_modal.widget import InputDialogWidget
    from misli.gui.views.message_box.widget import MessageBoxWidget

    set_main_loop(QtMainLoop())
    gui.set_util_provider(QtWidgetsUtilProvider())
