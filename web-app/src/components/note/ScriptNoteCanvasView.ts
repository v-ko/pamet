import { registerElementView } from "@/components/elementViewLibrary";
import { ScriptNote } from "@/model/ScriptNote";

import { calculateTextLayout } from "@/components/note/note-dependent-utils";
import { Point2D } from "fusion/primitives/Point2D";
import { NoteCanvasView } from "@/components/note/NoteCanvasView";
import { textRect } from "@/components/note/util";
import { DEFAULT_FONT_STRING } from "@/core/constants";
import { color_role_to_hex_color } from "@/util";

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
        let p1 = new Point2D([
            topRight.x - TRIANGLE_BASE - TRIANGLE_SPACING,
            topRight.y + TRIANGLE_SPACING]);
        let p2 = new Point2D([
            p1.x,
            p1.y + TRIANGLE_BASE]);
        let p3 = new Point2D([
            p1.x + TRIANGLE_BASE,
            p1.y + TRIANGLE_BASE / 2]);

        context.save();
        context.fillStyle = color_role_to_hex_color(note.style.color_role);
        context.beginPath();
        context.moveTo(p1.x, p1.y);
        context.lineTo(p2.x, p2.y);
        context.lineTo(p3.x, p3.y);
        context.fill();
    }
}

registerElementView(ScriptNote, ScriptNoteCanvasView)
