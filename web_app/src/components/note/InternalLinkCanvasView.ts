import { registerElementView } from "../../elementViewLibrary";
import { pamet } from "../../facade";
import { InternalLinkNote } from "../../model/InternalLinkNote";
import { Page } from "../../model/Page";
import { calculateTextLayout } from "../../util";
import { NoteCanvasView, BorderType, defaultFontString, textRect } from "./NoteCanvasView"

const MISSING_PAGE_TITLE = '(missing)'

export class InternalLinkNoteCanvasView extends NoteCanvasView {

    render(context: CanvasRenderingContext2D) {
        this.drawBackground(context);

        // Get page name
        let found = true;
        let note = this.noteViewState.note as InternalLinkNote
        let noteRect = note.rect();
        let pageId = note.targetPageId()
        let page: Page | undefined;
        if (pageId !== undefined) {
            let page = pamet.page(pageId)
            if (page === undefined) {
                found = false;
            }
        } else {
            found = false;
        }

        let text: string;
        if (found) {
            text = page!.name
        } else {
            text = MISSING_PAGE_TITLE
        }
        let textLayout = calculateTextLayout(text, textRect(noteRect), defaultFontString)
        this.drawText(context, textLayout);

        if (found) {
            this.drawBorder(context, BorderType.Solid)
        } else {
            this.drawBorder(context, BorderType.Dashed)
        }
    }
}

registerElementView(InternalLinkNote, InternalLinkNoteCanvasView)
