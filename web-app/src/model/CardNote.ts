import { textRect } from "../components/note/util";
import { entityType } from "fusion/libs/Entity";
import { Rectangle } from "../util/Rectangle";
import { Note } from "./Note";

const MIN_AR_DELTA_FOR_HORIZONTAL_ALIGN = 0.5
const IMAGE_PORTION_FOR_HORIZONTAL_ALIGN = 0.8

interface CardNoteLayout {
    textArea: Rectangle
    imageArea: Rectangle
}

@entityType('CardNote')
export class CardNote extends Note {
    layout(): CardNoteLayout {
        /**
         * Calculate the layout of the card note. The image fits in the note
         * and depending on the note size and image aspect ratio - takes either
         * a left-aligned position (max vertically) or a top position
         * (max horizontally), so that the image takes as much space as possible
         * and the text of the note serves as an annotation for it.
         */

        let imageArea: Rectangle;
        let textArea: Rectangle;

        // Get image aspect ratio or assume 1
        let imageAspectRatio = 1

        let image = this.content.image

        if (image !== undefined) {
            if (image.width > 0 && image.height > 0) {
                imageAspectRatio = image.width / image.height
            }
        }

        let noteRect = this.rect()
        let noteSize = noteRect.size()
        let noteAspectRatio = noteSize.x / noteSize.y

        let AR_delta = noteAspectRatio - imageAspectRatio
        if (AR_delta > MIN_AR_DELTA_FOR_HORIZONTAL_ALIGN) {
            // Image is tall in respect to the note, align the card horizontally
            imageArea = new Rectangle(
                noteRect.x,
                noteRect.y,
                noteSize.y * imageAspectRatio,
                noteSize.y
            )

            textArea = new Rectangle(
                noteRect.x + imageArea.width,
                noteRect.y,
                noteSize.x - imageArea.width,
                noteSize.y
            )
        } else { // Image is wide or similar to the note, align the card vertically
            imageArea = new Rectangle(
                noteRect.x,
                noteRect.y,
                noteSize.x,
                noteSize.y * IMAGE_PORTION_FOR_HORIZONTAL_ALIGN
            )
            textArea = new Rectangle(
                noteRect.x,
                noteRect.y + imageArea.height,
                noteSize.x,
                noteSize.y - imageArea.height
            )
        }
        return { textArea, imageArea }
    }
    textRect(): Rectangle {
        return textRect(this.layout().textArea)
    }
}
