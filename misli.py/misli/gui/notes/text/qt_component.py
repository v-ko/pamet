from PySide2.QtWidgets import QLabel
from PySide2.QtGui import QFontMetrics, QTextLayout, QPainter
from PySide2.QtCore import QSizeF, Qt, QRect, QRectF, QPointF

from misli.core.primitives import Color
from misli.constants import NOTE_MARGIN, NO_SCALE_LINE_SPACING
from misli.gui.base_component import Component


class TextNoteQtComponent(QLabel, Component):
    def __init__(self, parent_id):
        Component.__init__(self, parent_id, obj_class='Text')
        QLabel.__init__(self, 'dsa')

        self.elided_text = []
        self._alignment = Qt.AlignHCenter
        self.setMargin(0)

    def set_props(self, **props):
        palette = self.palette()

        fg_col = Color(*props['color']).to_QColor()
        bg_col = Color(*props['background_color']).to_QColor()

        palette.setColor(self.backgroundRole(), bg_col)
        palette.setColor(self.foregroundRole(), fg_col)

        self.setPalette(palette)

        x, y = props['x'], props['y']
        w, h = props['width'], props['height']
        self.setGeometry(QRect(x, y, w, h))

        font = self.font()
        # font.setPixelSize(20)
        # font.setPointSizeF(props['font_size'] * font.pointSizeF())
        font.setPointSizeF(14)
        self.setFont(font)

        # font_metrics = QFontMetrics(self.font())
        # print('Font ascent', font_metrics.ascent())
        # print('Font descent', font_metrics.descent())
        # print('Font height', font_metrics.height())
        # print('Font leading', font_metrics.leading())
        # print('Font lineSpacing', font_metrics.lineSpacing())
        # print('Font pointSizeF', self.font().pointSizeF())

        if 'text' in props:
            if '\n' in props['text']:
                self._alignment = Qt.AlignLeft
            else:
                self._alignment = Qt.AlignHCenter

            self.elided_text = self.elide_text(props['text'])

        # self.setText('<p style="line-height:%s%%;margin-top:-5px;margin-right
        # :5px;margin-bottom:5px">%s</p>' %
        #              (100*20/float(font_metrics.lineSpacing()), elided_text))
        # self.setText(elided_text)

    def paintEvent(self, event):
        if not self.elided_text:
            return

        painter = QPainter()
        painter.begin(self)

        # Qt configures the fonts with a lot of ascent
        # which makes them appear not properly centered
        hacky_padding = 10

        text_rect_height = self.rect().height() - 2 * NOTE_MARGIN
        _, first_rect = self.elided_text[0]
        _, last_rect = self.elided_text[-1]
        text_height = last_rect.bottom() - first_rect.top()
        vertical_offset = (text_rect_height - text_height) / 2
        vertical_offset -= hacky_padding / 2

        for line_text, elide_line_rect in self.elided_text:
            line_rect = QRectF(elide_line_rect)
            line_rect.moveTop(vertical_offset + line_rect.top())
            line_rect.setHeight(line_rect.height() + hacky_padding)
            after_rect = painter.drawText(
                line_rect, self._alignment | Qt.TextDontClip, line_text)

            # print(after_rect)
            # painter.drawRect(line_rect)
            # painter.drawRect(after_rect)

        painter.end()

    def elide_text(self, text):
        font_metrics = QFontMetrics(self.font())

        line_spacing = NO_SCALE_LINE_SPACING
        size = QSizeF(self.rect().size())
        size -= QSizeF(2 * NOTE_MARGIN, 2 * NOTE_MARGIN)
        text_rect = QRectF(QPointF(NOTE_MARGIN, NOTE_MARGIN), size)

        line_vpositions = []
        line_y = text_rect.top()
        while line_y <= text_rect.bottom() - line_spacing:
            line_vpositions.append(line_y)
            line_y += line_spacing

        text_lines = text.split('\n')
        eol_word_indices = []
        words = []

        for line in text_lines:
            words_on_line = line.split()
            words.extend(words_on_line)

            eol_word_indices.append(len(words) - 1)

        elided_text = []
        word_reached_idx = 0

        for line_y in line_vpositions:

            words_left = words[word_reached_idx:]
            line_rect = QRectF(text_rect)
            line_rect.moveTop(line_y)
            line_rect.setHeight(line_spacing)

            processed_words = 0

            width_left = text_rect.width()
            words_on_line = []

            # Fill the line with the words left from the text
            # (and elide where needed)
            for i, w in enumerate(words_left):
                word = w
                if i != 0:
                    word = ' ' + word

                word_bbox = font_metrics.boundingRect(word)

                if word_bbox.width() > width_left:
                    # If the first word's too long
                    # elide it and continue
                    if i == 0:
                        w = w[:-3] + '...'
                        processed_words += 1
                        words_on_line = [w]

                    # If we're on the last line
                    if i < (len(line_vpositions) - 1):
                        w = w[:3] + '...'
                        processed_words += 1
                        words_on_line.append(w)

                    break

                processed_words += 1
                width_left -= word_bbox.width()
                words_on_line.append(w)

                # Check if we're on EoL (because of a line break in the text)
                if (word_reached_idx + i) in eol_word_indices:
                    break

            if not words_on_line:
                break

            word_reached_idx += processed_words
            line_text = ' '.join(words_on_line)
            elided_text.append((line_text, line_rect))

        return elided_text

    def elide_text_old(self, text, rect):
        font_metrics = QFontMetrics(self.font())

        # lineSpacing = font_metrics.lineSpacing()
        line_spacing = NO_SCALE_LINE_SPACING
        size = rect.size()
        size -= QSizeF(2 * NOTE_MARGIN, 2 * NOTE_MARGIN)
        text_rect = QRectF(QPointF(NOTE_MARGIN, NOTE_MARGIN), size)

        text_layout = QTextLayout(text, self.font())
        text_layout.beginLayout()

        line_vpositions = []
        line_y = text_rect.top()
        while line_y <= text_rect.bottom() - line_spacing:
            line_vpositions.append(line_y)
            line_y += line_spacing

        elided_text = []

        for i, line_y in enumerate(line_vpositions):
            line = text_layout.createLine()

            if not line.isValid():
                break

            line.setLineWidth(text_rect.width())

            if i < (len(line_vpositions) - 1):  # Last line
                start_index = line.textStart()
                end_index = start_index + line.textLength()
                line_text = text[start_index:end_index]
            else:
                last_line = text[line.textStart():]
                line_text = font_metrics.elidedText(
                    last_line, Qt.ElideRight, text_rect.width())

            line_rect = QRectF(
                text_rect.left(), line_y, text_rect.width(), line_spacing)

            elided_text.append((line_text, line_rect))

        text_layout.endLayout()
        return elided_text
        # return '<br>'.join([t for t, r in elidedText])
