import { registerElementView } from "../elementViewLibrary";
import { ExternalLinkNote } from "../../model/ExternalLinkNote";

import { Point2D } from "fusion/primitives/Point2D";
import { CardNoteCanvasView } from "./CardNoteCanvasView";
import { color_role_to_hex_color } from "../../util";

const DECORATION_EDGE = 10;


export class ExternalLinkNoteCanvasView extends CardNoteCanvasView {
    render(context: CanvasRenderingContext2D) {
        super.render(context);
        this.drawBorder(context);

        // Fill a triangle in the upper right corner of the note
        let note = this.noteViewState.note() as ExternalLinkNote;
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
}

registerElementView(ExternalLinkNote, ExternalLinkNoteCanvasView)
