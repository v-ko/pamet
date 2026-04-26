import { registerElementView } from "@/views/elementViewLibrary";
import { CardNote } from "@/model/CardNote";
import { calculateTextLayout } from "@/views/note/note-dependent-utils";
import { BorderType, NoteCanvasView } from "@/views/note/NoteCanvasView";
import { textRect } from "@/views/note/util";
import { DEFAULT_FONT_STRING } from "@/app/constants";
import { Point2D } from "fusion/primitives/Point2D";
import { pamet } from "@/app/facade";

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
        // Project index header: render with solid border to indicate action on double-click
        if (note.metadata?.is_project_index_header) {
            this.drawBorder(context, BorderType.Solid);
        }

        if (note.content.page_ref) {
            // Solid if the linked page exists, dashed if it's missing
            let targetPage = pamet.page(note.content.page_ref.id);
            this.drawBorder(context, targetPage ? BorderType.Solid : BorderType.Dashed)
        } else if (note.hasExternalLink) {
            this.drawBorder(context);
            // Fill a triangle in the upper right corner of the note
            let p1 = note.rect().topRight();
            let p2 = p1.add(new Point2D([-DECORATION_EDGE, 0]));
            let p3 = p1.add(new Point2D([0, DECORATION_EDGE]));

            context.fillStyle = pamet.themeManager.canvasColor(note.style.color_role);
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
