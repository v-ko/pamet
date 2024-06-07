import { DEFAULT_BACKGROUND_COLOR, DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH, DEFAULT_TEXT_COLOR } from "../core/constants";
import { entityType, getEntityId } from "pyfusion/libs/Entity";
import { currentTime, timestamp } from "pyfusion/util";
import { elementId } from "./Element";
import { Note } from "./Note";

@entityType('TextNote')
export class TextNote extends Note {
    get text(): string {
        return this.content.text || '';
    }

    static default(pageId: string = ''): TextNote {
        let ownId = getEntityId();
        let id = elementId(pageId, ownId);

        return new TextNote({
            id: id,
            content: {
                text: ''
            },
            geometry: [0, 0, DEFAULT_NOTE_WIDTH, DEFAULT_NOTE_HEIGHT],
            style: {
                background_color: [...DEFAULT_BACKGROUND_COLOR],
                color: [...DEFAULT_TEXT_COLOR],
            },
            created: timestamp(currentTime()),
            modified:  timestamp(currentTime()),
            metadata: {},
            tags: []
        });
    }
}
