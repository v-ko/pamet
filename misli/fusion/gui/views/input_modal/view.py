from typing import Callable

import fusion
from fusion.gui import action
from fusion.gui import View


class InputDialogView(View):
    def __init__(self,
                 parent: str,
                 text: str,
                 result_callback: Callable,
                 default_value=None):
        View.__init__(self, parent)
        self.result_callback = result_callback

    @action('InputDialogView.finish_input')
    def finish_input(self):
        self.result_callback(self.textValue())
        fusion.remove_view(self)
