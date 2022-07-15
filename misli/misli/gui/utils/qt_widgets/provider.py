from PySide6.QtGui import QKeySequence, QShortcut, QCursor
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from misli import gui
from misli.gui import View
from misli.basic_classes import Rectangle, Point2D
from misli.gui.utils.base_provider import BaseUtilitiesProvider


# class FontMetrics:


class QtWidgetsUtilProvider(BaseUtilitiesProvider):
    def __init__(self):
        super().__init__()
        self._shortcuts = {}

    # def font_metrics(self, font):

    def add_key_binding(self, view, key_binding):
        shortcut = QShortcut(QKeySequence(key_binding.key), view)
        # shortcut.setContext(Qt.ApplicationShortcut)
        shortcut.activated.connect(
            key_binding.check_condition_and_invoke_command)

        self._shortcuts[id(key_binding)] = shortcut

    def remove_key_binding(self, key_binding):
        shortcut = self._shortcuts.pop(id(key_binding))
        if not shortcut:
            raise Exception(
                f'Cannot remove missing shortcut for {key_binding}')
        shortcut.setEnabled(False)
        shortcut.setParent(None)  # Not sure if that's enough to delete it

    def focused_view(self):
        focused_widget = QApplication.focusWidget()
        if not focused_widget:
            return None

        while not isinstance(focused_widget, gui.View):
            parent_widget = focused_widget.parent()
            if not parent_widget:
                raise Exception('Top level widget is not a View')
            focused_widget = parent_widget

        return focused_widget

    def set_focus(self, view):
        view.setFocus()

    def view_geometry(self, view):
        qrect = view.geometry()
        return Rectangle(qrect.x(), qrect.y(), qrect.width(), qrect.height())

    def map_from_global(self, view: View, point: Point2D):
        mapped = view.mapFromGlobal(QPoint(*point.as_tuple()))
        return Point2D(mapped.x(), mapped.y())

    def map_to_global(self, view: View, point: Point2D):
        mapped = view.mapToGlobal(QPoint(*point.as_tuple()))
        return Point2D(mapped.x(), mapped.y())

    def mouse_position(self):
        pos = QCursor.pos()
        return Point2D(pos.x(), pos.y())
