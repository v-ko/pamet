import { registerElementView } from "@/components/elementViewLibrary";
import { InternalLinkNote } from "@/model/InternalLinkNote";
import { calculateTextLayout } from "@/components/note/note-dependent-utils";
import { NoteCanvasView, BorderType } from "@/components/note/NoteCanvasView"
import { textRect } from "@/components/note/util";
import { DEFAULT_FONT_STRING } from "@/core/constants";


export class InternalLinkNoteCanvasView extends NoteCanvasView {

    render(context: CanvasRenderingContext2D) {
        this.drawBackground(context);

        // Get page name
        let note = this.noteViewState.note() as InternalLinkNote
        let text = note.text
        let textLayout = calculateTextLayout(text, textRect(note.rect()), DEFAULT_FONT_STRING)
        this.drawText(context, textLayout);

        if (note.targetPageId() !== undefined) {
            this.drawBorder(context, BorderType.Solid)
        } else {
            this.drawBorder(context, BorderType.Dashed)
        }
    }
}

registerElementView(InternalLinkNote, InternalLinkNoteCanvasView)
