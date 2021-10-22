from typing import Union
import misli
from misli.gui import View, action, Command


class ContextMenuView(View):
    def __init__(self, parent_id: str,
                 entries: dict[str, Union[Command, dict]]):
        View.__init__(self, parent_id=parent_id)
        self.entries = entries

    @action('ContextMenuView.close')
    def close(self):
        misli.gui.remove_view(self)
