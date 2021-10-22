from .logging import get_logger
from misli.entity_library import wrap_and_register_entity_type
from misli.entity_library.entity import Entity
from misli.entity_library.change import Change, ChangeTypes
from .pubsub import *
from misli.storage import set_repo, insert, remove, update, find, find_one
from . import gui


def configure_for_qt():
    from misli.gui.qt_main_loop import QtMainLoop
    from misli.gui.utils.qt_widgets.provider import QtWidgetsUtilProvider
    set_main_loop(QtMainLoop())
    gui.set_util_provider(QtWidgetsUtilProvider())
