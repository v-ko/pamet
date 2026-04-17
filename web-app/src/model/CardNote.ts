import { textRect } from "@/views/note/util";
import { entityType, getEntityId } from "fusion/model/Entity";
import { Rectangle, RectangleData } from "fusion/primitives/Rectangle";
import { Note, NoteData } from "@/model/Note";
import { Page } from "@/model/Page";
import { currentTime, timestamp } from "fusion/util/base";
import { DEFAULT_BACKGROUND_COLOR_ROLE, DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH, DEFAULT_TEXT_COLOR_ROLE } from "@/core/constants";

const MIN_AR_DELTA_FOR_HORIZONTAL_ALIGN = 0.5
const IMAGE_PORTION_FOR_HORIZONTAL_ALIGN = 0.8

export interface CardNoteLayout {
    textArea?: Rectangle
    imageArea?: Rectangle
}

@entityType('CardNote')
export class CardNote extends Note {
    static createNew(props: Partial<NoteData> & { pageId: string }): Note {
        let id = getEntityId()

        let noteData: NoteData = {
            id: id,
            parent_id: props.pageId,
            content: {
                text: ''
            },
            geometry: [0, 0, DEFAULT_NOTE_WIDTH, DEFAULT_NOTE_HEIGHT] as RectangleData,
            style: {
                background_color_role: DEFAULT_BACKGROUND_COLOR_ROLE,
                color_role: DEFAULT_TEXT_COLOR_ROLE,
            },
            created: timestamp(currentTime()),
            modified: timestamp(currentTime()),
            metadata: {}
        }
        noteData = Object.assign(noteData, props);
        return new CardNote(noteData);
    }
    static createInternalLinkNote(targetPage: Page, parentId: string): CardNote {
        let id = getEntityId();
        let currentTimestamp = timestamp(currentTime());

        let note = new CardNote({
            id,
            parent_id: parentId,
            content: {
                text: targetPage.name,
                page_ref: { id: targetPage.id, path: targetPage.path },
            },
            geometry: [0, 0, 200, 100],
            style: {
                background_color_role: 'primary',
                color_role: 'onPrimary',
            },
            created: currentTimestamp,
            modified: currentTimestamp,
            metadata: {}
        });
        return note;
    }

    layout(): CardNoteLayout {
        let noteRect = this.rect();
        let hasText = this.content.text;
        let hasImage = this.content.image;

        let textArea: Rectangle | undefined;
        let imageArea: Rectangle | undefined;

        if (hasText && !hasImage) {
            textArea = noteRect;
        } else if (!hasText && hasImage) {
            imageArea = noteRect;
        } else if (hasText && hasImage) {
            let imageAspectRatio = 1;
            if (hasImage.width > 0 && hasImage.height > 0) {
                imageAspectRatio = hasImage.width / hasImage.height;
            }

            let noteSize = noteRect.size();
            let noteAspectRatio = noteSize.x / noteSize.y;

            let AR_delta = noteAspectRatio - imageAspectRatio;
            if (AR_delta > MIN_AR_DELTA_FOR_HORIZONTAL_ALIGN) {
                // Image is tall in respect to the note, align the card horizontally
                imageArea = new Rectangle([
                    noteRect.x,
                    noteRect.y,
                    noteSize.y * imageAspectRatio,
                    noteSize.y
                ]);

                textArea = new Rectangle([
                    noteRect.x + imageArea.width,
                    noteRect.y,
                    noteSize.x - imageArea.width,
                    noteSize.y
                ]);
            } else { // Image is wide or similar to the note, align the card vertically
                imageArea = new Rectangle([
                    noteRect.x,
                    noteRect.y,
                    noteSize.x,
                    noteSize.y * IMAGE_PORTION_FOR_HORIZONTAL_ALIGN
                ]);
                textArea = new Rectangle([
                    noteRect.x,
                    noteRect.y + imageArea.height,
                    noteSize.x,
                    noteSize.y - imageArea.height
                ]);
            }
        }

        return { textArea, imageArea };
    }
    textRect(): Rectangle {
        let textArea = this.layout().textArea;
        if (!textArea) {
            throw new Error('Trying to get the text area of a CardNote without text area defined.');
        }
        return textRect(textArea)
    }

    get hasInternalPageLink(): boolean {  // If refactoring change the index configs for Pamet
        return this.content.page_ref !== undefined
    }
    get hasExternalLink(): boolean | undefined {  // If refactoring change the index configs for Pamet
        return !!this.content.url
    }
}
