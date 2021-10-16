from typing import Callable

import misli
from misli import action
from misli.gui import View


class InputDialogView(View):
    def __init__(self,
                 parent_id: str,
                 text: str,
                 result_callback: Callable,
                 default_value=None):
        View.__init__(self, parent_id)
        self.result_callback = result_callback

    @action('InputDialogView.finish_input')
    def finish_input(self):
        self.result_callback(self.textValue())
        misli.remove_view(self)
