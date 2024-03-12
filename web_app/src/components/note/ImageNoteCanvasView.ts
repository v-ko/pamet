import { registerElementView } from "../../elementViewLibrary";
import { pamet } from "../../facade";
import { ImageNote } from "../../model/ImageNote";
import { calculateTextLayout } from "../../util";
import { NoteCanvasView, defaultFontString, textRect } from "./NoteCanvasView";

const IMAGE_MISSING_TEXT = '(image missing)'
const IMAGE_NOT_LOADED_TEXT = '(loading...)'

export class ImageNoteCanvasView extends NoteCanvasView {
    render(context: CanvasRenderingContext2D) {
        let note = this.noteViewState.note;
        let [x, y, w, h] = note.geometry;
        let imageMetadata = note.content.image;
        if (imageMetadata === undefined) {
            // Display error text instead
            let textLayout = calculateTextLayout(IMAGE_MISSING_TEXT, textRect(note.rect()), defaultFontString)
            this.drawBackground(context);
            this.drawText(context, textLayout);
            return;
        }

        let image = this.renderer.getImage(pamet.pametSchemaToHttpUrl(imageMetadata.url));
        let errorText: string | undefined = undefined;
        if (image === null) { // element is not mounted (initial render or internal error)
            errorText = IMAGE_NOT_LOADED_TEXT;
        } else if (!image.complete) { // still loading
            errorText = IMAGE_NOT_LOADED_TEXT;
        } else if (image.naturalWidth === 0) { // loaded unsuccessfully
            errorText = IMAGE_MISSING_TEXT;
        }
        if (errorText !== undefined) {
            let textLayout = calculateTextLayout(errorText, textRect(this.noteViewState.note.rect()), defaultFontString)
            this.drawBackground(context);
            this.drawText(context, textLayout);
            return;
        }

        this.drawBackground(context);
        console.log('Drawing image', image, x, y, w, h)
        context.drawImage(image!, x, y, w, h);
    }
}

registerElementView(ImageNote, ImageNoteCanvasView)
