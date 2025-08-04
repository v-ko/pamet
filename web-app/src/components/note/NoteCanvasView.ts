import { NoteViewState } from "./NoteViewState";
import { NO_SCALE_LINE_SPACING } from "../../core/constants";
import { TextLayout } from "../../util";
import { color_role_to_hex_color } from "../../util/Color";
import { calculateTextLayout } from "./note-dependent-utils";
import { Point2D } from "../../util/Point2D";
import { Rectangle } from "../../util/Rectangle";
import { BaseCanvasView } from "./BaseCanvasView";
import { pamet } from "../../core/facade";
import { DEFAULT_FONT_STRING } from "../../core/constants";
import { textRect, imageRect } from "./util";
import { Size } from "../../util/Size";
import { getLogger } from "fusion/logging";
import { ImageNote } from "../../model/ImageNote";

let log = getLogger('NoteCanvasView');



const IMAGE_MISSING_TEXT = '(image missing)'
const IMAGE_NOT_LOADED_TEXT = '(loading...)'



export enum BorderType {
    Solid,
    Dashed,
}

export abstract class NoteCanvasView extends BaseCanvasView {

    get noteViewState(): NoteViewState {
        return this.elementViewState as NoteViewState;
    }

    drawBackground(context: CanvasRenderingContext2D) {
        let note = this.noteViewState.note();
        let backgroundColor = color_role_to_hex_color(note.style.background_color_role);
        context.fillStyle = backgroundColor;
        context.fillRect(note.geometry[0], note.geometry[1], note.geometry[2], note.geometry[3]);
    }

    drawText(context: CanvasRenderingContext2D, textLayout: TextLayout) {

        context.save()

        let note = this.noteViewState.note();
        let color = color_role_to_hex_color(note.style.color_role);

        const textRect_ = textRect(textLayout.textRect)
        const textTopLeft = textRect_.topLeft();

        // Center align vertically in textRect
        let textHeight = textLayout.lines.length * NO_SCALE_LINE_SPACING;
        textTopLeft.y = textTopLeft.y + (textRect_.height - textHeight) / 2;

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
            adjTopLeft.x = adjTopLeft.x + textRect_.width / 2;
        }

        // Draw text
        context.font = DEFAULT_FONT_STRING;
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
        let note = this.noteViewState.note();
        context.save()
        context.strokeStyle = color_role_to_hex_color(note.style.color_role);
        context.lineWidth = 1;
        if (borderType === BorderType.Dashed) {
            context.setLineDash([10, 5]);
        }
        context.strokeRect(note.geometry[0], note.geometry[1], note.geometry[2], note.geometry[3]);
        context.restore()
    }

    drawImage(context: CanvasRenderingContext2D, imageArea: Rectangle) {
        let note = this.noteViewState.note();
        if (!(note instanceof ImageNote)) {
            log.error('drawImage called on non-ImageNote', note);
            return;
        }
        let noteRect = note.rect();
        let imageMetadata = note.content.image;
        if (imageMetadata === undefined) {
            // Display error text instead
            let textLayout = calculateTextLayout(IMAGE_MISSING_TEXT, textRect(noteRect), DEFAULT_FONT_STRING)
            this.drawText(context, textLayout);
            return;
        }

        // Use the MediaItem's projectScopedUrl method
        let mediaItem = note.imageMediaItem();
        let userId = pamet.appViewState.userId;
        let projectId = pamet.appViewState.currentProjectId;
        if (userId === null || projectId === null) {
            log.error('Cannot draw image: userId or projectId is undefined');
            return;
        }
        let mediaItemRoute = mediaItem.pametRoute(userId, projectId);

        let image = this.renderer.getImage(mediaItemRoute.toRelativeReference());
        let errorText: string | undefined = undefined;
        if (image === null) { // element is not mounted (initial render or internal error)
            errorText = IMAGE_NOT_LOADED_TEXT;
        } else if (!image.complete) { // still loading
            errorText = IMAGE_NOT_LOADED_TEXT;
        } else if (image.naturalWidth === 0) { // loaded unsuccessfully
            errorText = IMAGE_MISSING_TEXT;
        }
        if (errorText !== undefined) {
            let textLayout = calculateTextLayout(errorText, textRect(noteRect), DEFAULT_FONT_STRING)
            this.drawText(context, textLayout);
            return;
        }

        let imgRect = imageRect(imageArea, new Size(image!.naturalWidth, image!.naturalHeight));
        context.drawImage(image!, imgRect.x, imgRect.y, imgRect.w, imgRect.h);
    }

    abstract render(context: CanvasRenderingContext2D): void;
}
