import { registerElementView } from "../../elementViewLibrary";
import { CardNote } from "../../model/CardNote";
import { ImageNote } from "../../model/ImageNote";
import { TextNote } from "../../model/TextNote";
import { calculateTextLayout } from "../../util";
import { Rectangle } from "../../util/Rectangle";
import { NoteCanvasView, defaultFontString, textRect } from "./NoteCanvasView";

const MIN_AR_DELTA_FOR_HORIZONTAL_ALIGN = 0.5
const IMAGE_PORTION_FOR_HORIZONTAL_ALIGN = 0.8

interface CardNoteLayout {
    textArea: Rectangle
    imageArea: Rectangle
}

export class CardNoteCanvasView extends NoteCanvasView {
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

        let note = this.noteViewState.note
        let image = note.content.image

        if (image !== undefined) {
            if (image.width > 0 && image.height > 0) {
                imageAspectRatio = image.width / image.height
            }
        }

        let noteRect = note.rect()
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
                noteRect.x + imageArea.width(),
                noteRect.y,
                noteSize.x - imageArea.width(),
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
                noteRect.y + imageArea.height(),
                noteSize.x,
                noteSize.y - imageArea.height()
            )
        }
        return { textArea, imageArea }
    }
    render(context: CanvasRenderingContext2D) {
        let note = this.noteViewState.note
        let noteRect = note.rect();

        let hasText = note.content.text !== undefined
        let hasImage = note.content.image !== undefined

        // In all cases - draw the background
        this.drawBackground(context)

        // If there's no content - draw the background and finish
        if (!hasText && !hasImage) {
            return
        } else if (hasText && !hasImage) { // Only text
            let text = note.content.text || '';
            let textLayout = calculateTextLayout(text, textRect(noteRect), defaultFontString);
            this.drawText(context, textLayout);

        } else if (!hasText && hasImage) { // Only image
            this.drawImage(context, noteRect)
        } else { // Both text and image
            let layout = this.layout()
            let textRect_ = textRect(layout.textArea)
            let textLayout = calculateTextLayout(note.content.text || '', textRect_, defaultFontString)
            this.drawText(context, textLayout)
            this.drawImage(context, layout.imageArea)
        }

        // console.log('DRAWING CARD NOTE')
        // console.log(note.rect(), layout, textLayout)

        // // Draw the layout for debugging
        // context.save()
        // context.strokeStyle = 'red'
        // context.lineWidth = 1
        // context.strokeRect(layout.textArea.x, layout.textArea.y, layout.textArea.width(), layout.textArea.height())
        // context.strokeStyle = 'blue'
        // context.strokeRect(layout.imageArea.x, layout.imageArea.y, layout.imageArea.width(), layout.imageArea.height())
        // context.restore()
    }
}

registerElementView(TextNote, CardNoteCanvasView)
registerElementView(ImageNote, CardNoteCanvasView)
registerElementView(CardNote, CardNoteCanvasView)
