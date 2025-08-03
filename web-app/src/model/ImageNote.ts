import { imageRect } from "../components/note/util";
import { entityType, getEntityId } from "fusion/libs/Entity";
import { Rectangle } from "../util/Rectangle";
import { Size } from "../util/Size";
import { Note } from "./Note";
import { MediaItem, MediaItemData } from "./MediaItem";
import { elementId } from "./Element";
import { RectangleData } from "../util/Rectangle";
import { DEFAULT_BACKGROUND_COLOR_ROLE, DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH, DEFAULT_TEXT_COLOR_ROLE } from "../core/constants";
import { currentTime, timestamp } from "fusion/util";

@entityType('ImageNote')
export class ImageNote extends Note {
    static createNew(pageId: string, mediaItem: MediaItem): ImageNote {
        let ownId = getEntityId();
        let id = elementId(pageId, ownId);

        let noteData = {
            id: id,
            content: {
                image: mediaItem._data as MediaItemData
            },
            geometry: [0, 0, DEFAULT_NOTE_WIDTH, DEFAULT_NOTE_HEIGHT] as RectangleData,
            style: {
                background_color_role: DEFAULT_BACKGROUND_COLOR_ROLE,
                color_role: DEFAULT_TEXT_COLOR_ROLE,
            },
            created: timestamp(currentTime()),
            modified: timestamp(currentTime()),
            metadata: {},
            tags: []
        }
        return new ImageNote(noteData);
    }

    imageMediaItem(): MediaItem {
        let image = this.content.image;
        if (image === undefined) {
            throw Error('ImageNote has no image');
        }
        return new MediaItem(image);
    }

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
