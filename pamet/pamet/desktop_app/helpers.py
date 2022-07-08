from typing import List, Tuple

from PySide6.QtGui import QGuiApplication, QFontMetrics, QPainter
from PySide6.QtCore import Qt, QRectF, QPointF, QSizeF, QRect

from pamet.constants import NOTE_MARGIN, NO_SCALE_LINE_SPACING


def control_is_pressed():
    return QGuiApplication.queryKeyboardModifiers() & Qt.ControlModifier


def shift_is_pressed():
    return QGuiApplication.queryKeyboardModifiers() & Qt.ShiftModifier


class TextLayout:
    def __init__(self):
        self.data = []
        self.is_elided = False

    def text(self):
        return '\n'.join([text for text, line in self.data])


def elide_text(text, text_rect, font) -> TextLayout:
    font_metrics = QFontMetrics(font)

    # Get the needed parameters
    line_spacing = NO_SCALE_LINE_SPACING

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
    text_layout = TextLayout()
    ellide_line_end = False
    word_reached_idx = 0
    ellipsis_width = font_metrics.boundingRect('...').width()

    for line_idx, line_y in enumerate(line_vpositions):
        words_left = words[word_reached_idx:]

        # Find the coordinates and dimentions of the line
        line_rect = QRectF(*text_rect.as_tuple())
        line_rect.moveTop(line_y)
        line_rect.setHeight(line_spacing)

        # Fill the line word by word
        words_on_line = []
        width_left = text_rect.width()
        used_words = 0

        for word_idx_on_line, word in enumerate(words_left):
            # Add a leading space except before the first word
            if word_idx_on_line != 0:
                word = ' ' + word

            at_the_last_line = line_idx == (len(line_vpositions) - 1)
            at_last_word = word_idx_on_line == (len(words_left) - 1)

            # Get the dimentions of the word if drawn
            word_bbox = font_metrics.boundingRect(word)

            # There's enough space on the line for the next word
            if width_left >= word_bbox.width():
                width_left -= word_bbox.width()
                words_on_line.append(word)
                used_words += 1

            else:  # There's not enough space for the next word

                # If there's no room to add an elided word - ellide the
                # previous
                if at_the_last_line and width_left < ellipsis_width:
                    # words_on_line[-1] = words_on_line[-1]
                    ellide_line_end = True

                # Elide if we're past the end of the last line
                # or if it's the first word on the line and it's just too long
                if at_the_last_line or word_idx_on_line == 0:
                    word = font_metrics.elidedText(
                        word, Qt.ElideRight, width_left)
                    text_layout.is_elided = True
                    words_on_line.append(word)
                    used_words += 1

                # Done with this line - break and start the next if any
                break

            # Check if we're on EoL (because of a line break in the text)
            if (word_reached_idx + word_idx_on_line) in eol_word_indices:
                if at_the_last_line and not at_last_word:
                    ellide_line_end = True
                break

        if not words_on_line:
            break

        word_reached_idx += used_words
        line_text = ''.join(words_on_line)

        if ellide_line_end:
            text_layout.is_elided = True
            if len(line_text) >= 3:
                line_text = line_text[:-3] + '...'
            else:
                line_text = '...'

        text_layout.data.append((line_text, line_rect))
    pass
    return text_layout


def draw_text_lines(
        painter: QPainter,
        text_layout: List[Tuple[str, QRectF]],
        alignment: Qt.AlignmentFlag,
        text_rect: QRect):
    if not text_layout:
        return
    # Qt configures the fonts with a lot of ascent
    # which makes them appear not properly centered
    hacky_padding = 8

    text_rect_height = text_rect.height()
    first_rect = text_layout[0][1]
    last_rect = text_layout[-1][1]
    text_height = last_rect.bottom() - first_rect.top()
    vertical_offset = (text_rect_height - text_height) / 2
    vertical_offset -= hacky_padding / 2

    for line_text, elide_line_rect in text_layout:
        line_rect = QRectF(elide_line_rect)
        line_rect.moveTop(vertical_offset + line_rect.top())
        line_rect.setHeight(line_rect.height() + hacky_padding)
        after_rect = painter.drawText(
            line_rect, alignment | Qt.TextDontClip, line_text)

        # print(after_rect)
        # painter.drawRect(line_rect)
        # painter.drawRect(after_rect)
