import { entityType, getEntityId } from "fusion/model/Entity";
import { RectangleData } from "fusion/primitives/Rectangle";
import { Note } from "@/model/Note";
import { elementId } from "@/model/Element";
import { DEFAULT_BACKGROUND_COLOR_ROLE, DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH, DEFAULT_TEXT_COLOR_ROLE } from "@/core/constants";
import { currentTime, timestamp } from "fusion/util/base";

@entityType('ImageNote')
export class ImageNote extends Note {
    static createNew(pageId: string): ImageNote {
        let ownId = getEntityId();
        let id = elementId(pageId, ownId);

        let noteData = {
            id: id,
            content: {
                image_id: ''  // Media items have the note for parent, so no use in setting something here for now
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
}
