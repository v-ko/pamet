from typing import Callable, Union
from PySide6.QtWidgets import QLabel, QMenu, QWidgetAction
from PySide6.QtGui import QCursor, QKeySequence
from PySide6.QtCore import Qt

import fusion
from fusion.libs.command import Command

SEPARATOR = '---'


def add_entries(menu: QMenu, entries):
    for name, command in entries.items():
        # Nested dicts mean submenus
        if isinstance(command, dict):
            submenu = QMenu(name, menu)
            add_entries(submenu, command)
            menu.addMenu(submenu)
        elif command is None:
            label_action = QWidgetAction(menu)
            label = QLabel(name)
            label.setAlignment(Qt.AlignCenter)
            label_action.setDefaultWidget(label)
            menu.addAction(label_action)
        elif isinstance(command, Callable):
            binding = None  # first_key_binding_for_command(command)
            if binding:
                menu.addAction(name, command, QKeySequence(binding.key))
            else:
                menu.addAction(name, command)
        elif command is SEPARATOR:
            menu.addSeparator()
        else:
            raise Exception


class ContextMenuWidget(QMenu):

    def __init__(self, parent: str, entries: dict[str, Union[Command, dict]]):
        QMenu.__init__(self, parent)

        add_entries(self, entries)

        self.aboutToHide.connect(self.hiding)

        # This should probably be done via a state update
        fusion.call_delayed(self.popup_on_mouse_pos, 0)

    def popup_on_mouse_pos(self):
        position = QCursor.pos()
        self.popup(position)

    def hiding(self):
        self.close()

    def close(self):
        self.deleteLater()
