from PySide2.QtGui import QFont

DEFAULT_FONT_SIZE = 13  # LineSpacing = 20. Grid match


def defaultFont():
    font = QFont('Halvetica')
    font.setStyleStrategy(font.PreferAntialias)
    font.setHintingPreference(font.PreferNoHinting)
    font.setPointSizeF(DEFAULT_FONT_SIZE)

    return font
