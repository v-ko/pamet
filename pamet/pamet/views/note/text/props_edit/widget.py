from PySide6.QtWidgets import QWidget
from .ui_widget import Ui_TextEditPropsWidget


class TextEditPropsWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.ui = Ui_TextEditPropsWidget()
        self.ui.setupUi(self)
