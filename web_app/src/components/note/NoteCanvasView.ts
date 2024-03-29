import { NoteViewState } from "./NoteViewState";
import { DEFAULT_NOTE_FONT_FAMILY, DEFAULT_NOTE_FONT_FAMILY_GENERIC, DEFAULT_NOTE_FONT_SIZE, DEFAULT_NOTE_LINE_HEIGHT, NOTE_MARGIN, NO_SCALE_LINE_SPACING } from "../../constants";
import { TextLayout, calculateTextLayout, color_to_css_rgba_string } from "../../util";
import { Point2D } from "../../util/Point2D";
import { Rectangle } from "../../util/Rectangle";
import { BaseCanvasView } from "./BaseCanvasView";
import { pamet } from "../../facade";



export const defaultFontString = `${DEFAULT_NOTE_FONT_SIZE}px/${DEFAULT_NOTE_LINE_HEIGHT}px ` +
    `'${DEFAULT_NOTE_FONT_FAMILY}', ` +
    `${DEFAULT_NOTE_FONT_FAMILY_GENERIC}`;


const IMAGE_MISSING_TEXT = '(image missing)'
const IMAGE_NOT_LOADED_TEXT = '(loading...)'



export function textRect(forArea: Rectangle): Rectangle {
    return new Rectangle(
        forArea.x + NOTE_MARGIN,
        forArea.y + NOTE_MARGIN,
        forArea.w - 2 * NOTE_MARGIN,
        forArea.h - 2 * NOTE_MARGIN);
}


export function imageRect(forArea: Rectangle, imageSize: Point2D): Rectangle {
    /**
     * Returns a centered rectangle, keeping the image aspect ratio
     */
    let size = forArea.size();
    let imageAR = imageSize.x / imageSize.y;
    let areaAR = size.x / size.y;
    let imageRect: Rectangle;

    if (imageAR > areaAR) {
        let w = size.x;
        let h = w / imageAR;
        imageRect = new Rectangle(forArea.x, forArea.y + (size.y - h) / 2, w, h);
    } else if (imageAR < areaAR) {
        let h = size.y;
        let w = h * imageAR;
        imageRect = new Rectangle(forArea.x + (size.x - w) / 2, forArea.y, w, h);
    } else {
        imageRect = new Rectangle(forArea.x, forArea.y, forArea.w, forArea.h);
    }
    return imageRect
}

export enum BorderType {
    Solid,
    Dashed,
}

export abstract class NoteCanvasView extends BaseCanvasView {

    get noteViewState(): NoteViewState {
        return this.elementViewState as NoteViewState;
    }

    drawBackground(context: CanvasRenderingContext2D) {
        let note = this.noteViewState.note;
        let backgroundColor = color_to_css_rgba_string(note.style.background_color);
        context.fillStyle = backgroundColor;
        context.fillRect(note.geometry[0], note.geometry[1], note.geometry[2], note.geometry[3]);
    }

    drawText(context: CanvasRenderingContext2D, textLayout: TextLayout) {

        context.save()

        let note = this.noteViewState.note;
        let color = color_to_css_rgba_string(note.style.color);

        const textRect_ = textRect(textLayout.textRect)
        const textTopLeft = textRect_.topLeft();

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

    drawImage(context: CanvasRenderingContext2D, imageArea: Rectangle) {
        let note = this.noteViewState.note;
        let noteRect = note.rect();
        let imageMetadata = note.content.image;
        if (imageMetadata === undefined) {
            // Display error text instead
            let textLayout = calculateTextLayout(IMAGE_MISSING_TEXT, textRect(noteRect), defaultFontString)
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
            let textLayout = calculateTextLayout(errorText, textRect(noteRect), defaultFontString)
            this.drawText(context, textLayout);
            return;
        }

        let imgRect = imageRect(imageArea, new Point2D(image!.naturalWidth, image!.naturalHeight));
        context.drawImage(image!, imgRect.x, imgRect.y, imgRect.w, imgRect.h);
    }

    abstract render(context: CanvasRenderingContext2D): void;
}
