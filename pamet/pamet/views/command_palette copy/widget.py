from PySide6.QtWidgets import QWidget
from misli.gui.utils.qt_widgets.qtview import QtView
from misli.gui.view_library.view_state import ViewState, view_state_type
from .ui_widget import Ui_CommandPaletteWidget


@view_state_type
class CommandPaletteViewState(ViewState):
    pass


class CommandPaletteWidget(QWidget, QtView):
    def __init__(self, parent, initial_state):
        super().__init__(parent)
        QtView.__init__(self, initial_state)

        self.ui = Ui_CommandPaletteWidget()
        self.ui.setupUi(self)
