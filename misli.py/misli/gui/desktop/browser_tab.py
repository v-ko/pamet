from PySide2.QtWidgets import QVBoxLayout, QWidget

from misli import misli, log
from misli.objects import BaseObject
from misli.gui.containers import page_classes


class BrowserTab(QWidget, BaseObject):
    def __init__(self, **kwargs):
        parent = kwargs.get('parent', None)

        QWidget.__init__(parent=parent)
        BaseObject.__init__(**kwargs)

        self.setLayout(QVBoxLayout())

    def clear_layout(self):
        layout = self.layout()

        for i in range(layout.count()):
            layout.removeWidget(layout.itemAt(i))

    def set_state(self, state_dict):
        self.page_name = state_dict.pop('page_name', None)

        if self.page_name:
            self.clear_layout()
            # new_page_state = misli.find_page(name=self.page_name)
            #
            # if not new_page_state:
            #     log.error(
            #         '[%s] No page with name %s' % (str(self), self.page_name))
            #     return

            page_component = misli.init_components_for_page(self.page_name)
            # PageClass = page_classes.get(new_page_state.page_class, None)
            # if not PageClass:
            #     log.error('No such page type', new_page_state.page_class)
            #     return
            #
            # page = PageClass()
            # page.set_props(new_page_state.asdict())

            self.layout().addWidget(page_component)
