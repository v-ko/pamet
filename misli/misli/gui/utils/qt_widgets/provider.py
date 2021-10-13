from typing import List

from misli import gui
from misli.gui.utils.base_provider import BaseUtilitiesProvider


class QtWidgetsUtilProvider(BaseUtilitiesProvider):
    def mount_view(self, view):
        view.setParent(gui.view(view.parent_id))

    def unmount_view(self, view):
        view.deleteLater()
