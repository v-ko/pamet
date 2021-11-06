from typing import Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

import misli
from misli.gui import register_view_type
from .view import MessageBoxView


@register_view_type(name='MessageBox')
class MessageBoxWidget(MessageBoxView, QMessageBox):
    def __init__(self, parent_id: str, title: str, text: str):
        parent = misli.gui.view(parent_id)
        MessageBoxView.__init__(self, parent_id, '', title, text)
        QMessageBox.__init__(self, QMessageBox.Information, title, text,
                             QMessageBox.Ok)

        # Center the dialog
        geometry = self.geometry()
        geometry.moveCenter(parent.geometry().center())
        self.setGeometry(geometry)

        self.finished.connect(self.handle_dismissed)
        self.show()
