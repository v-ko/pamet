import { NOTE_MARGIN } from "../../core/constants";
import { Rectangle } from "../../util/Rectangle";
import { Size } from "../../util/Size";

export function textRect(forArea: Rectangle): Rectangle {
    return new Rectangle(
        forArea.x + NOTE_MARGIN,
        forArea.y + NOTE_MARGIN,
        forArea.w - 2 * NOTE_MARGIN,
        forArea.h - 2 * NOTE_MARGIN);
}


export function imageGeometryToFitAre(forArea: Rectangle, imageSize: Size): Rectangle {
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
    return imageRect;
}

