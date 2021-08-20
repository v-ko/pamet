from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt


def control_is_pressed():
    return QGuiApplication.queryKeyboardModifiers() & Qt.ControlModifier


def shift_is_pressed():
    return QGuiApplication.queryKeyboardModifiers() & Qt.ShiftModifier
