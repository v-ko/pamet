from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QTextEdit, QWidget
from .ui_widget import Ui_TextEditPropsWidget

TEXT_EDIT_MIN_SIZE = 30


class FixedTextEdit(QTextEdit):
    """The default QTextEdit implementation has an inflexible (borderline
    buggy) size constraints, which cannot be overwriteen in any other way."""
    def minimumSizeHint(self) -> QSize:
        return QSize(TEXT_EDIT_MIN_SIZE, TEXT_EDIT_MIN_SIZE)

    def sizeHint(self) -> QSize:
        return QSize(TEXT_EDIT_MIN_SIZE, TEXT_EDIT_MIN_SIZE)


class TextEditPropsWidget(QWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.ui = Ui_TextEditPropsWidget()
        self.ui.setupUi(self)

        layout = self.layout()
        self.ui.text_edit = FixedTextEdit(self)
        layout.addWidget(self.ui.text_edit)
        self.setLayout(layout)
