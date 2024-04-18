import { registerElementView } from "../../elementViewLibrary";
import { ScriptNote } from "../../model/ScriptNote";
import { color_to_css_rgba_string } from "../../util";
import { calculateTextLayout } from "./util";
import { Point2D } from "../../util/Point2D";
import { NoteCanvasView } from "./NoteCanvasView";
import { textRect } from "./util";
import { DEFAULT_FONT_STRING } from "../../constants";

const TRIANGLE_BASE = 10;
const TRIANGLE_SPACING = 3;

export class ScriptNoteCanvasView extends NoteCanvasView {
    render(context: CanvasRenderingContext2D) {
        let note = this.noteViewState.note() as ScriptNote
        let noteRect = note.rect();
        let text = note.content.text || '';
        let textLayout = calculateTextLayout(text, textRect(noteRect), DEFAULT_FONT_STRING);

        this.drawBackground(context);
        this.drawText(context, textLayout);
        this.drawBorder(context);

        // Draw a play icon in the upper right corner of the note
        let topRight = note.rect().topRight();
        let p1 = new Point2D(
            topRight.x - TRIANGLE_BASE - TRIANGLE_SPACING,
            topRight.y + TRIANGLE_SPACING);
        let p2 = new Point2D(
            p1.x,
            p1.y + TRIANGLE_BASE);
        let p3 = new Point2D(
            p1.x + TRIANGLE_BASE,
            p1.y + TRIANGLE_BASE / 2);

        context.save();
        context.fillStyle = color_to_css_rgba_string(note.style.color);
        context.beginPath();
        context.moveTo(p1.x, p1.y);
        context.lineTo(p2.x, p2.y);
        context.lineTo(p3.x, p3.y);
        context.fill();
    }
}

registerElementView(ScriptNote, ScriptNoteCanvasView)
