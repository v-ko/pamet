from typing import Union
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import QPoint

import misli
from misli.gui import register_view_type, Command

from .view import ContextMenuView


@register_view_type
class ContextMenuWidget(ContextMenuView, QMenu):
    def __init__(self, parent_id: str,
                 entries: dict[str, Union[Command, dict]], position):
        ContextMenuView.__init__(parent_id, entries)
        QMenu.__init__(misli.gui.view(parent_id))

        for name, command in entries.items():
            # Nested dicts mean submenus
            if isinstance(command, dict):
                submenu = ContextMenuWidget(self, command)
                self.addMenu(submenu)
            else:
                qaction = QAction(name)
                qaction.setShortcut(QKeySequence(command.shortcut))
                qaction.triggered.connect(command)
                self.addAction(qaction)

        self.aboutToHide.connect(lambda: ContextMenuView.close(self))

        self.popup(QPoint(*position.to_list()))
