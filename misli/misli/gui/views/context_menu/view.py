from typing import Union
import misli
from misli.gui import View, action, Command


class ContextMenuView(View):
    def __init__(self, parent_id: str,
                 entries: dict[str, Union[Command, dict]], position):
        self.entries = entries
        self.position = position

    @action('ContextMenuView.close')
    def close(self):
        misli.remove_view(self)
