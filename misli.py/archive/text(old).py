from PySide2.QtWidgets import QLabel
from PySide2.QtGui import QColor, QFontMetrics, QTextLayout
from PySide2.QtCore import QSizeF, Qt, QRectF, QPointF
from misli import log
from misli.constants import NOTE_MARGIN


class TextNoteComponent(QLabel):
    def __init__(self, note, parent=None):
        super(TextNoteComponent, self).__init__('loading', parent=parent)

        self.note = note
        if not parent:
            log.warning('Text note %s initialized without parent', note)
            return

        palette = self.palette()

        bg_col = QColor(*[c*255 for c in self.note.bg_col])
        fg_col = QColor(*[c*255 for c in self.note.txt_col])

        palette.setColor(self.backgroundRole(), bg_col)
        palette.setColor(self.foregroundRole(), fg_col)

        self.setPalette(palette)

        self.setTextFormat(Qt.MarkdownText)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.setMargin(NOTE_MARGIN)

        self.setPalette(palette)
        self.setState(note)

    def setState(self, note):
        self.setText(self.elideText(note.text))

    def elideText(self, text):
        fontMetrics = QFontMetrics(self.font())

        # print('Font ascent', fontMetrics.ascent())
        # print('Font descent', fontMetrics.descent())
        # print('Font height', fontMetrics.height())
        # print('Font leading', fontMetrics.leading())
        # print('Font lineSpacing', fontMetrics.lineSpacing())
        # print('Font pointSizeF', self.font().pointSizeF())

        lineSpacing = fontMetrics.lineSpacing()

        size = self.note.rect.size()
        size -= QSizeF(2 * NOTE_MARGIN, 2 * NOTE_MARGIN)
        idealTextRect = QRectF(QPointF(NOTE_MARGIN, NOTE_MARGIN), size)
        textRect = idealTextRect

        textLayout = QTextLayout(self.note.text, self.font())
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
                lineText = self.note.text[startIndex:endIndex]
            else:
                lastLine = self.note.text[line.textStart():]
                lineText = fontMetrics.elidedText(
                    lastLine, Qt.ElideRight, textRect.width())

            lineRect = QRectF(
                textRect.left(), lineY, textRect.width(), lineSpacing)

            elidedText.append((lineText, lineRect))

        textLayout.endLayout()

        # return elidedText
        return ''.join([t for t, r in elidedText])
