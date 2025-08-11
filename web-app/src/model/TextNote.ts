import { DEFAULT_BACKGROUND_COLOR_ROLE, DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH, DEFAULT_TEXT_COLOR_ROLE } from "@/core/constants";
import { entityType, getEntityId } from "fusion/libs/Entity";
import { currentTime, timestamp } from "fusion/base-util";
import { elementId } from "@/model/Element";
import { Note } from "@/model/Note";
import { RectangleData } from "fusion/primitives/Rectangle";

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
                background_color_role: DEFAULT_BACKGROUND_COLOR_ROLE,
                color_role: DEFAULT_TEXT_COLOR_ROLE,
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
