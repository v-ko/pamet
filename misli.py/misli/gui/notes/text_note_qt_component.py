from PySide2.QtWidgets import QLabel
from PySide2.QtGui import QColor, QFontMetrics, QTextLayout
from PySide2.QtCore import QSizeF, Qt, QRectF, QPointF, QRect
# from PySide2.QtGui import QFontMetrics

from misli.gui.desktop import defaultFont
# from misli import log
from misli.gui.constants import NOTE_MARGIN
from misli.gui.component import Component
from misli.objects import Note


class TextNoteQtComponent(QLabel, Component):
    def __init__(self, parent_id):
        Component.__init__(self, parent_id)
        QLabel.__init__(self, '')

        self.note = None

        self.setTextFormat(Qt.MarkdownText)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.setMargin(NOTE_MARGIN)
        self.setHidden(True)

        # fontMetrics = QFontMetrics(self.widget.font())

        # print('Font ascent', fontMetrics.ascent())
        # print('Font descent', fontMetrics.descent())
        # print('Font height', fontMetrics.height())
        # print('Font leading', fontMetrics.leading())
        # print('Font lineSpacing', fontMetrics.lineSpacing())
        # print('Font pointSizeF', self.widget.font().pointSizeF())
        # if self.widget.font().pointSizeF() != 13:
        #     print(self.note)

    def set_props(self, **kwargs):
        note = Note(**kwargs)
        self.note = note

        palette = self.palette()

        bg_col = QColor(*[c*255 for c in note.bg_col])
        fg_col = QColor(*[c*255 for c in note.txt_col])

        palette.setColor(self.backgroundRole(), bg_col)
        palette.setColor(self.foregroundRole(), fg_col)

        self.setPalette(palette)

        rect = QRect(*note.rect())

        self.setGeometry(rect)  # 0, 0, width, height)

        font = defaultFont()
        font.setPointSizeF(note.font_size * font.pointSizeF())
        self.setFont(font)

        elided_text = self.elide_text(note.text, QRectF(*note.rect()))
        self.setText(elided_text)

    def elide_text(self, text, rect):
        fontMetrics = QFontMetrics(self.font())

        # print('Font ascent', fontMetrics.ascent())
        # print('Font descent', fontMetrics.descent())
        # print('Font height', fontMetrics.height())
        # print('Font leading', fontMetrics.leading())
        # print('Font lineSpacing', fontMetrics.lineSpacing())
        # print('Font pointSizeF', self.font().pointSizeF())

        lineSpacing = fontMetrics.lineSpacing()

        size = rect.size()
        size -= QSizeF(2 * NOTE_MARGIN, 2 * NOTE_MARGIN)
        idealTextRect = QRectF(QPointF(NOTE_MARGIN, NOTE_MARGIN), size)
        textRect = idealTextRect

        textLayout = QTextLayout(text, self.font())
        textLayout.beginLayout()

        lineVPositions = []
        line_y = textRect.top()
        while line_y <= textRect.bottom() - lineSpacing:
            lineVPositions.append(line_y)
            line_y += lineSpacing

        elidedText = []

        for i, lineY in enumerate(lineVPositions):
            line = textLayout.createLine()

            if not line.isValid():
                break

            line.setLineWidth(textRect.width())

            if i < (len(lineVPositions) - 1):  # Last line
                startIndex = line.textStart()
                endIndex = startIndex + line.textLength()
                lineText = text[startIndex:endIndex]
            else:
                lastLine = text[line.textStart():]
                lineText = fontMetrics.elidedText(
                    lastLine, Qt.ElideRight, textRect.width())

            lineRect = QRectF(
                textRect.left(), lineY, textRect.width(), lineSpacing)

            elidedText.append((lineText, lineRect))

        textLayout.endLayout()

        return ''.join([t for t, r in elidedText])
