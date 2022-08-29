from typing import Callable, List

import fusion
from fusion.gui import View, action


class MessageBoxView(View):
    def __init__(self,
                 parent: str,
                 title: str,
                 text: str):
        View.__init__(self, parent)

    @action('MessageBoxView.handle_dismissed')
    def handle_dismissed(self):
        fusion.remove_view(self)
