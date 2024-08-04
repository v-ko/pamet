import { DEFAULT_BACKGROUND_COLOR, DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH, DEFAULT_TEXT_COLOR } from "../core/constants";
import { entityType, getEntityId } from "fusion/libs/Entity";
import { currentTime, timestamp } from "fusion/util";
import { elementId } from "./Element";
import { Note } from "./Note";
import { RectangleData } from "../util/Rectangle";
import { ColorData } from "../util";

@entityType('TextNote')
export class TextNote extends Note {
    static createNew(pageId: string = ''): Note {
        let ownId = getEntityId();
        let id = elementId(pageId, ownId);

        let noteData = {
            id: id,
            content: {
                text: ''
            },
            geometry: [0, 0, DEFAULT_NOTE_WIDTH, DEFAULT_NOTE_HEIGHT] as RectangleData,
            style: {
                background_color: [...DEFAULT_BACKGROUND_COLOR] as ColorData,
                color: [...DEFAULT_TEXT_COLOR] as ColorData,
            },
            created: timestamp(currentTime()),
            modified:  timestamp(currentTime()),
            metadata: {},
            tags: []
        }
        return new TextNote(noteData);
    }

    get text(): string {
        return this.content.text || '';
    }
}
