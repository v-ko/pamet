from typing import List, Tuple

from PySide6.QtGui import QGuiApplication, QFontMetrics, QPainter
from PySide6.QtCore import Qt, QRectF, QPointF, QSizeF, QRect

from pamet.constants import NOTE_MARGIN, NO_SCALE_LINE_SPACING


def control_is_pressed():
    return QGuiApplication.queryKeyboardModifiers() & Qt.ControlModifier


def shift_is_pressed():
    return QGuiApplication.queryKeyboardModifiers() & Qt.ShiftModifier


def elide_text(text, rect, font) -> List[Tuple[str, QRectF]]:
    font_metrics = QFontMetrics(font)

    # Get the needed parameters
    line_spacing = NO_SCALE_LINE_SPACING
    size = QSizeF(rect.size())
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


def draw_text_lines(
        painter: QPainter,
        text_layout: List[Tuple[str, QRectF]],
        alignment: Qt.AlignmentFlag,
        draw_rect: QRect):

    # Qt configures the fonts with a lot of ascent
    # which makes them appear not properly centered
    hacky_padding = 8

    text_rect_height = draw_rect.height() - 2 * NOTE_MARGIN
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
