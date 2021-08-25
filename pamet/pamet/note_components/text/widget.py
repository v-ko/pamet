from dataclasses import dataclass

from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QFontMetrics, QTextLayout, QPainter, QColor, QFont
from PySide6.QtCore import QSizeF, Qt, QRect, QRectF, QPointF

from misli import Entity, register_entity
from misli.gui.view_library import register_view_class
from pamet.constants import NOTE_MARGIN, NO_SCALE_LINE_SPACING
from pamet.note_components.base_note_view import NoteView
from pamet.entities import Note

from misli import get_logger
log = get_logger(__name__)


@register_entity
@dataclass
class NoteViewModel(Entity):
    note: Note = None


@register_view_class(obj_type='TextNote', edit=False)
class TextNoteViewWidget(QLabel, NoteView):
    def __init__(self, parent_id):
        NoteView.__init__(
            self, parent_id=parent_id, initial_model=NoteViewModel())
        QLabel.__init__(self, '')

        self.elided_text = []
        self._alignment = Qt.AlignHCenter
        self.setMargin(0)

    def handle_model_update(self, old_state, new_state):
        note = self.note
        palette = self.palette()

        fg_col = QColor(*note.get_color().to_uint8_rgba_list())
        bg_col = QColor(*note.get_background_color().to_uint8_rgba_list())

        palette.setColor(self.backgroundRole(), bg_col)
        palette.setColor(self.foregroundRole(), fg_col)

        self.setPalette(palette)
        self.setGeometry(QRect(*note.rect().as_tuple()))

        font = self.font()
        # font.setPixelSize(20)
        # font.setPointSizeF(note_props['font_size'] * font.pointSizeF())
        font.setPointSizeF(14)
        self.setFont(font)

        # font_metrics = QFontMetrics(self.font())
        # print('Font ascent', font_metrics.ascent())
        # print('Font descent', font_metrics.descent())
        # print('Font height', font_metrics.height())
        # print('Font leading', font_metrics.leading())
        # print('Font lineSpacing', font_metrics.lineSpacing())
        # print('Font pointSizeF', self.font().pointSizeF())

        if '\n' in note.text:
            self._alignment = Qt.AlignLeft
        else:
            self._alignment = Qt.AlignHCenter

        self.elided_text = self.elide_text(note.text)

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

        # Get the needed parameters
        line_spacing = NO_SCALE_LINE_SPACING
        size = QSizeF(self.rect().size())
        size -= QSizeF(2 * NOTE_MARGIN, 2 * NOTE_MARGIN)
        text_rect = QRectF(QPointF(NOTE_MARGIN, NOTE_MARGIN), size)

        # Get the y coordinates of the lines
        line_vpositions = []
        line_y = text_rect.top()
        while line_y <= text_rect.bottom() - line_spacing:
            line_vpositions.append(line_y)
            line_y += line_spacing

        # Divide the text into words and "mark" the ones ending with am
        # EoL char (by keeping their indexes in eol_word_indices)
        words = []
        eol_word_indices = []

        for line in text.split('\n'):
            words_on_line = line.split()
            words.extend(words_on_line)
            eol_word_indices.append(len(words) - 1)

        # Start filling the available lines one by one
        elided_text = []
        word_reached_idx = 0

        for line_idx, line_y in enumerate(line_vpositions):
            words_left = words[word_reached_idx:]

            # Find the coordinates and dimentions of the line
            line_rect = QRectF(text_rect)
            line_rect.moveTop(line_y)
            line_rect.setHeight(line_spacing)

            # Fill the line word by word
            words_on_line = []
            width_left = text_rect.width()
            used_words = 0

            for word_idx, word in enumerate(words_left):
                # Add a leading space except before the first word
                if word_idx != 0:
                    word = ' ' + word

                # Get the dimentions of the word if drawn
                word_bbox = font_metrics.boundingRect(word)

                # if there's not enough space for the next word
                if width_left < word_bbox.width():
                    at_the_last_line = line_idx == (len(line_vpositions) - 1)

                    # Elide if the word that's longer than the line (no wrap)
                    # and elide if we're past the end of the last line
                    if at_the_last_line or word_idx == 0:
                        word = font_metrics.elidedText(
                            word, Qt.ElideRight, width_left)
                        # log.info('ELIDED WORD: %s' % word)

                        words_on_line.append(word)
                        used_words += 1
                        break

                    # If there's more lines available - go to the next
                    else:
                        break

                # If there's still space on this line
                else:
                    width_left -= word_bbox.width()
                    words_on_line.append(word)
                    used_words += 1

                if width_left <= 0:  # Just for the case where w == 0 I guess
                    break

                # Check if we're on EoL (because of a line break in the text)
                if (word_reached_idx + word_idx) in eol_word_indices:
                    break

            if not words_on_line:
                break

            word_reached_idx += used_words
            line_text = ''.join(words_on_line)
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
