import { registerElementView } from "../elementViewLibrary";
import { CardNote } from "../../model/CardNote";
import { ImageNote } from "../../model/ImageNote";
import { TextNote } from "../../model/TextNote";
import { calculateTextLayout } from "./util";
import { NoteCanvasView } from "./NoteCanvasView";
import { textRect } from "./util";
import { DEFAULT_FONT_STRING } from "../../core/constants";



export class CardNoteCanvasView extends NoteCanvasView {

    render(context: CanvasRenderingContext2D) {
        let note = this.noteViewState.note() as CardNote;
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
            let textLayout = calculateTextLayout(text, textRect(noteRect), DEFAULT_FONT_STRING);
            this.drawText(context, textLayout);

        } else if (!hasText && hasImage) { // Only image
            this.drawImage(context, noteRect)
        } else { // Both text and image
            let layout = note.layout()
            let textRect_ = textRect(layout.textArea)
            let textLayout = calculateTextLayout(note.content.text || '', textRect_, DEFAULT_FONT_STRING)
            this.drawText(context, textLayout)
            this.drawImage(context, layout.imageArea)
        }

        // console.log('DRAWING CARD NOTE')
        // console.log(note.rect(), layout, textLayout)

        // // Draw the layout for debugging
        // context.save()
        // context.strokeStyle = 'red'
        // context.lineWidth = 1
        // context.strokeRect(layout.textArea.x, layout.textArea.y, layout.textArea.width, layout.textArea.height)
        // context.strokeStyle = 'blue'
        // context.strokeRect(layout.imageArea.x, layout.imageArea.y, layout.imageArea.width, layout.imageArea.height)
        // context.restore()
    }
}

registerElementView(TextNote, CardNoteCanvasView)
registerElementView(ImageNote, CardNoteCanvasView)
registerElementView(CardNote, CardNoteCanvasView)
