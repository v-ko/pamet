from PySide6.QtGui import QFont, QFontDatabase

from pamet import desktop_app
from pamet.util import resource_path


def setup_fonts_and_icons():
    desktop_app.icons.load_all()

    _font_id = QFontDatabase.addApplicationFont(
        str(resource_path("fonts/OpenSans-VariableFont_wdth,wght.ttf"))
    )
    _font_family = QFontDatabase.applicationFontFamilies(_font_id)[0]
    _default_note_font = QFont(_font_family)
    _default_note_font.setPointSizeF(14)
    desktop_app.set_default_note_font(_default_note_font)
