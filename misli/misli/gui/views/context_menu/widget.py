from typing import Union
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import QPoint

import misli
from misli.gui.key_binding_manager import first_key_binding_for_command
from misli.gui import register_view_type, Command

from .view import ContextMenuView


def add_entries(menu, entries):
    for name, command in entries.items():
        # Nested dicts mean submenus
        if isinstance(command, dict):
            submenu = QMenu(name, menu)
            add_entries(submenu, command)
            menu.addMenu(submenu)
        else:
            binding = first_key_binding_for_command(command)
            if binding:
                menu.addAction(name, command, QKeySequence(binding.key))
            else:
                menu.addAction(name, command)


@register_view_type(name='ContextMenu')
class ContextMenuWidget(ContextMenuView, QMenu):
    def __init__(self, parent_id: str,
                 entries: dict[str, Union[Command, dict]]):
        ContextMenuView.__init__(self, parent_id, entries)
        parent = misli.gui.view(parent_id)
        QMenu.__init__(self, parent)

        add_entries(self, entries)

        self.aboutToHide.connect(self.hiding)

        # This should probably be done via a state update
        misli.call_delayed(self.popup_on_mouse_pos, 0)

    def popup_on_mouse_pos(self):
        position = misli.gui.util_provider().mouse_position()
        self.popup(QPoint(*position.as_tuple()))

    def hiding(self):
        ContextMenuView.close(self)
        print('HIDING')