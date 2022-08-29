from typing import Callable
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog

import fusion
# from fusion.gui import register_view_type
from .view import InputDialogView


# @register_view_type
class InputDialogWidget(InputDialogView, QInputDialog):
    def __init__(self,
                 parent: str,
                 text: str,
                 result_callback: Callable,
                 default_value=None):
        parent = fusion.gui.view(parent.id)
        InputDialogView.__init__(self,
                                 parent,
                                 '',
                                 text,
                                 result_callback)
        QInputDialog.__init__(self, parent, Qt.Widget)

        self.setLabelText(text)
        if default_value:
            self.setTextValue(default_value)

        # Center the dialog
        geometry = self.geometry()
        geometry.moveCenter(parent.geometry().center())
        self.setGeometry(geometry)

        self.finished.connect(self.finish_input)

        self.input_widget.setFocus()
        self.show()

    def focusOutEvent(self, event):
        self.finish_input()
