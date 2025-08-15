import { registerElementView } from "@/components/elementViewLibrary";
import { CardNote } from "@/model/CardNote";
import { calculateTextLayout } from "@/components/note/note-dependent-utils";
import { BorderType, NoteCanvasView } from "@/components/note/NoteCanvasView";
import { textRect } from "@/components/note/util";
import { DEFAULT_FONT_STRING } from "@/core/constants";
import { Point2D } from "fusion/primitives/Point2D";
import { color_role_to_hex_color } from "@/util";

const DECORATION_EDGE = 10;


export class CardNoteCanvasView extends NoteCanvasView {

    render(context: CanvasRenderingContext2D) {
        let note = this.noteViewState.note() as CardNote;

        // In all cases - draw the background
        this.drawBackground(context)
        let layout = note.layout();

        // Draw note content (text and image)
        if (layout.textArea) {
            let textRect_ = textRect(layout.textArea);
            let textLayout = calculateTextLayout(note.content.text || '', textRect_, DEFAULT_FONT_STRING);
            this.drawText(context, textLayout);
        }

        if (layout.imageArea) {
            this.drawImage(context, layout.imageArea);
        }

        // Draw link decorations
        let internalLinkRoute = note.internalLinkRoute();
        if (internalLinkRoute) {
            if (internalLinkRoute.pageId) { // This is a bit of a hack
                this.drawBorder(context, BorderType.Solid)
            } else {
                this.drawBorder(context, BorderType.Dashed)
            }
        } else if (note.hasExternalLink) {
            this.drawBorder(context);
            // Fill a triangle in the upper right corner of the note
            let p1 = note.rect().topRight();
            let p2 = p1.add(new Point2D([-DECORATION_EDGE, 0]));
            let p3 = p1.add(new Point2D([0, DECORATION_EDGE]));

            context.fillStyle = color_role_to_hex_color(note.style.color_role);
            context.beginPath();
            context.moveTo(p1.x, p1.y);
            context.lineTo(p2.x, p2.y);
            context.lineTo(p3.x, p3.y);
            context.fill();
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

registerElementView(CardNote, CardNoteCanvasView)
