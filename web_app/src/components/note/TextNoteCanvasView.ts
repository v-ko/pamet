import { registerElementView } from "../../elementViewLibrary";
import { InternalLinkNote } from "../../model/InternalLinkNote";
import { TextNote } from "../../model/TextNote";
import { NoteCanvasView } from "./NoteCanvasView";

export class TextNoteCanvasView extends NoteCanvasView {

    render(context: CanvasRenderingContext2D) {
        const textLayout = this.noteViewState.textLayoutData;
        this.drawBackground(context);
        this.drawText(context, textLayout);
    }
}

registerElementView(TextNote, TextNoteCanvasView)
registerElementView(InternalLinkNote, TextNoteCanvasView)
