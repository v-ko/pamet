from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from misli import gui
from misli.gui import View, ViewState, wrap_and_register_view_state_type
from misli.gui.view_library import register_view_type


@wrap_and_register_view_state_type
class BrowserTabViewState(ViewState):
    name: str = ''
    page_view_id: str = None
    edit_view_id: str = None


@register_view_type
class BrowserTabViewWidget(QWidget, View):
    def __init__(self, parent_id):
        QWidget.__init__(self)
        View.__init__(
            self,
            parent_id=parent_id,
            initial_state=BrowserTabViewState()
        )

        self.page_view = None

        # Widget config
        self.setLayout(QVBoxLayout())

    def on_state_update(self):
        new_model = self.state

        if not self.page_view or \
                (self.previous_state.page_view_id != new_model.page_view_id):
            if new_model.page_view_id:
                self.switch_to_page_view(new_model.page_view_id)

            else:
                raise Exception('Empty page_view_id passed')

    def on_child_added(self, child):
        # If we're adding an edit component
        if type(child) in gui.view_library.get_view_classes(edit=True):
            # Setup the editing component
            child.setParent(self)
            child.setWindowFlag(Qt.Sheet, True)

            child.show()

    def on_child_removed(self, child):
        if type(child) in gui.view_library.get_view_classes(edit=True):
            child.close()

    def switch_to_page_view(self, page_view_id):
        if self.page_view:
            self.layout().removeWidget(self.page_view)

        page_view = gui.view(page_view_id)
        self.layout().addWidget(page_view)

        self.page_view = page_view
