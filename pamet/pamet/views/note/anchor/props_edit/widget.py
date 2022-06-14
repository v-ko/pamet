from PySide6.QtWidgets import QWidget
from .ui_widget import Ui_AnchorEditPropsWidget


class AnchorEditPropsWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.ui = Ui_AnchorEditPropsWidget()
        self.ui.setupUi(self)
