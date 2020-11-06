from PySide2.QtGui import QFontMetrics

from misli.gui import defaultFont
from misli.gui.notes import note_component


class NoteWidgetBox(object):
    def __init__(self, note, parent=None):

        self._note = None
        self.widget = None
        self.parent = parent

        # Runtime
        self._selected = False

        # Cache
        self.qpainter_command_cache = None

        self.setNote(note)

    def isSelected(self):
        return self._selected

    def setSelected(self, selected):
        self._selected = selected

    @property
    def note(self):
        return self._note

    def setNote(self, note):
        self._note = note

        NoteComponentClass = note_component(note.obj_type)
        self.widget = NoteComponentClass(note, parent=self.parent)

        width = note.rect.size().width()
        height = note.rect.size().height()

        self.widget.setGeometry(0, 0, width, height)
        self.widget.setHidden(True)

        font = defaultFont()
        font.setPointSizeF(self.note.font_size * font.pointSizeF())

        self.widget.setFont(font)
        fontMetrics = QFontMetrics(self.widget.font())

        self.widget.setState(self.note)

        print('Font ascent', fontMetrics.ascent())
        print('Font descent', fontMetrics.descent())
        print('Font height', fontMetrics.height())
        print('Font leading', fontMetrics.leading())
        print('Font lineSpacing', fontMetrics.lineSpacing())
        print('Font pointSizeF', self.widget.font().pointSizeF())
        if self.widget.font().pointSizeF() != 13:
            print(self.note)
