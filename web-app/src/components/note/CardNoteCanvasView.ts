import { registerElementView } from "@/components/elementViewLibrary";
import { CardNote } from "@/model/CardNote";
import { ImageNote } from "@/model/ImageNote";
import { TextNote } from "@/model/TextNote";
import { calculateTextLayout } from "@/components/note/note-dependent-utils";
import { NoteCanvasView } from "@/components/note/NoteCanvasView";
import { textRect } from "@/components/note/util";
import { DEFAULT_FONT_STRING } from "@/core/constants";



export class CardNoteCanvasView extends NoteCanvasView {

    render(context: CanvasRenderingContext2D) {
        let note = this.noteViewState.note();
        let noteRect = note.rect();

        // In all cases - draw the background
        this.drawBackground(context)

        // Render based on note type, most specific first
        if (note instanceof CardNote) { // Must be first because it extends both TextNote and ImageNote
            let layout = note.layout()
            let textRect_ = textRect(layout.textArea)
            let textLayout = calculateTextLayout(note.content.text || '', textRect_, DEFAULT_FONT_STRING)
            this.drawText(context, textLayout)
            this.drawImage(context, layout.imageArea)
        } else if (note instanceof ImageNote) {
            this.drawImage(context, noteRect)
        } else if (note instanceof TextNote) {
            let text = note.content.text || '';
            let textLayout = calculateTextLayout(text, textRect(noteRect), DEFAULT_FONT_STRING);
            this.drawText(context, textLayout);
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
