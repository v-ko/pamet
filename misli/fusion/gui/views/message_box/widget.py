from typing import Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

import fusion
# from fusion.gui import register_view_type
from .view import MessageBoxView


# @register_view_type(name='MessageBox')
class MessageBoxWidget(MessageBoxView, QMessageBox):
    def __init__(self, parent: str, title: str, text: str):
        MessageBoxView.__init__(self, parent, '', title, text)
        QMessageBox.__init__(self, QMessageBox.Information, title, text,
                             QMessageBox.Ok)

        # Center the dialog
        geometry = self.geometry()
        geometry.moveCenter(parent.geometry().center())
        self.setGeometry(geometry)

        self.finished.connect(self.handle_dismissed)
        self.show()
