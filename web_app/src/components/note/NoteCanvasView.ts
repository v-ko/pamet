import { NoteViewState } from "./NoteViewState";
import { DEFAULT_NOTE_FONT_FAMILY, DEFAULT_NOTE_FONT_FAMILY_GENERIC, DEFAULT_NOTE_FONT_SIZE, DEFAULT_NOTE_LINE_HEIGHT, NOTE_MARGIN, NO_SCALE_LINE_SPACING } from "../../constants";
import { TextLayoutData, color_to_css_rgba_string } from "../../util";
import { Point2D } from "../../util/Point2D";
import { Rectangle } from "../../util/Rectangle";
import { BaseCanvasView } from "./BaseCanvasView";



export const defaultFontString = `${DEFAULT_NOTE_FONT_SIZE}px/${DEFAULT_NOTE_LINE_HEIGHT}px ` +
    `'${DEFAULT_NOTE_FONT_FAMILY}', ` +
    `${DEFAULT_NOTE_FONT_FAMILY_GENERIC}`;




export function textRect(forArea: Rectangle): Rectangle {
    let size = forArea.size();
    size = size.subtract(new Point2D(2 * NOTE_MARGIN, 2 * NOTE_MARGIN));
    return new Rectangle(NOTE_MARGIN, NOTE_MARGIN, size.x, size.y);
}


export enum BorderType {
    Solid,
    Dashed,
}

export abstract class NoteCanvasView extends BaseCanvasView{

    get noteViewState(): NoteViewState {
        return this.elementViewState as NoteViewState;
    }

    drawBackground(context: CanvasRenderingContext2D) {
        let note = this.noteViewState.note;
        let backgroundColor = color_to_css_rgba_string(note.style.background_color);
        context.fillStyle = backgroundColor;
        context.fillRect(note.geometry[0], note.geometry[1], note.geometry[2], note.geometry[3]);
    }

    drawText(context: CanvasRenderingContext2D, textLayout: TextLayoutData) {

        context.save()

        let note = this.noteViewState.note;
        let color = color_to_css_rgba_string(note.style.color);

        const noteRect = note.rect();
        const textRect_ = textRect(note.rect())
        const textTopLeft = new Point2D(
            noteRect.x + textRect_.x,
            noteRect.y + textRect_.y);

        // Center align vertically in textRect
        let textHeight = textLayout.lines.length * NO_SCALE_LINE_SPACING;
        textTopLeft.y = textTopLeft.y + (textRect_.height() - textHeight) / 2;

        // Adjust for the text body to be drawn in the middle of the line
        let adjTopLeft = new Point2D(textTopLeft.x, textTopLeft.y);
        let hackyPadding = NO_SCALE_LINE_SPACING / 7.5; // TODO: Should be dependent on font descent
        adjTopLeft.y = adjTopLeft.y + hackyPadding;

        // // Debug: draw the translatedtextrect with a red border
        // textRect.setTopLeft(textTopLeft);
        // textRect.setHeight(textHeight);
        // ctx.strokeStyle = 'red';
        // ctx.lineWidth = 1;
        // ctx.strokeRect(textRect.x, textRect.y, textRect.width(), textRect.height());

        // Correct for ctx center align behavior
        if (textLayout.alignment === 'center') {
            adjTopLeft.x = adjTopLeft.x + textRect_.width() / 2;
        }

        // Draw text
        context.font = defaultFontString;
        context.textBaseline = 'top';
        context.textAlign = textLayout.alignment;
        context.fillStyle = color;
        for (let i = 0; i < textLayout.lines.length; i++) {
            context.fillText(
                textLayout.lines[i],
                adjTopLeft.x,
                adjTopLeft.y + i * NO_SCALE_LINE_SPACING,
            );

            // // Debug: Draw line bounding box
            // ctx.strokeStyle = 'blue';
            // ctx.lineWidth = 1;
            // ctx.strokeRect(textTopLeft.x, textTopLeft.y + i * NO_SCALE_LINE_SPACING, textRect.width(), NO_SCALE_LINE_SPACING);
        }
        context.restore();
    }

    drawBorder(context: CanvasRenderingContext2D, borderType: BorderType = BorderType.Solid) {
        let note = this.noteViewState.note;
        context.save()
        context.strokeStyle = color_to_css_rgba_string(note.style.color);
        context.lineWidth = 1;
        if (borderType === BorderType.Dashed) {
            context.setLineDash([10, 5]);
        }
        context.strokeRect(note.geometry[0], note.geometry[1], note.geometry[2], note.geometry[3]);
        context.restore()
    }

    abstract render(context: CanvasRenderingContext2D): void;
}
