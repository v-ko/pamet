import { imageRect } from "../components/note/util";
import { entityType } from "fusion/libs/Entity";
import { Rectangle } from "../util/Rectangle";
import { Size } from "../util/Size";
import { Note } from "./Note";

@entityType('ImageNote')
export class ImageNote extends Note {
    imageRect(): Rectangle {
        let image = this.content.image!;
        if (image === undefined) {
            throw Error('ImageNote has no image');
        }
        if (image.width <= 0 && image.height <= 0) {
            throw Error('ImageNote has no image size');
        }
        return imageRect(this.rect(), new Size(image.width, image.height));
    }
}
