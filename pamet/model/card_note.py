
from copy import copy
from typing import Tuple
from fusion.util.point2d import Point2D
from fusion.util.rectangle import Rectangle
from fusion.libs.entity import entity_type
from pamet.constants import NOTE_MARGIN
from pamet.model.image_note import ImageNote
from pamet.model.text_note import TextNote

MIN_AR_DELTA_FOR_HORIZONTAL_ALIGN = 0.5
IMAGE_PORTION_FOR_HORIZONTAL_ALIGN = 0.8


@entity_type
class CardNote(ImageNote, TextNote):
    def image_and_text_rects(self,
                             for_size: Point2D = None
                             ) -> Tuple[Rectangle, Rectangle]:
        """Returns the rectangles where the image and text should fit.
        They are relative to the note view"""
        image_rect = Rectangle(0, 0, 0, 0)
        text_rect = Rectangle(0, 0, 0, 0)

        # Fit the image in the note
        # If there's no image - assume rectangular
        image_size = self.image_size
        if image_size:
            image_aspect_ratio = image_size.x() / image_size.y()
        else:
            image_aspect_ratio = 1

        if for_size:
            note_size = for_size
        else:
            note_size = self.size()
        note_aspect_ratio = note_size.x() / note_size.y()
        ar_delta = note_aspect_ratio - image_aspect_ratio
        if ar_delta > MIN_AR_DELTA_FOR_HORIZONTAL_ALIGN:
            # Calc image size from AR
            image_rect.set_size(
                Point2D(note_size.y() * image_aspect_ratio, note_size.y()))
            # Prep the field (will apply margins below)
            text_field = Rectangle(*image_rect.top_right().as_tuple(),
                                   note_size.x() - image_rect.width(),
                                   note_size.y())

        else:
            # Decide on a good image to text ratio. E.g. 5:1 vertically
            # Image rect
            image_field = Rectangle(
                0, 0, note_size.x(),
                note_size.y() * IMAGE_PORTION_FOR_HORIZONTAL_ALIGN)
            image_field_AR = image_field.width() / image_field.height()
            if image_field_AR > image_aspect_ratio:
                # The avalable space is wider than the image
                image_rect.set_size(
                    Point2D(image_field.height() * image_aspect_ratio,
                            image_field.height()))
            else:
                # The available space is higher (when we fit the image width)
                image_rect.set_size(
                    Point2D(image_field.width(),
                            image_field.width() / image_aspect_ratio))
                image_field = copy(image_rect)

            image_rect.move_center(image_field.center())

            # Text rect
            text_field = Rectangle(image_field.bottom_left().x(),
                                   image_field.bottom_left().y(),
                                   note_size.x(),
                                   note_size.y() - image_field.height())

        # Apply margins to get the text field
        text_rect = text_field
        text_rect.set_top_left(text_rect.top_left() +
                               Point2D(NOTE_MARGIN, NOTE_MARGIN))
        text_rect.set_size(text_rect.size() -
                           Point2D(2 * NOTE_MARGIN, 2 * NOTE_MARGIN))

        return image_rect, text_rect

    def image_rect(self, for_size: Point2D = None):
        return self.image_and_text_rects(for_size)[0]

    def text_rect(self, for_size: Point2D = None):
        return self.image_and_text_rects(for_size)[1]
