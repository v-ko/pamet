import { textRect } from "@/components/note/util";
import { entityType, getEntityId } from "fusion/model/Entity";
import { Rectangle, RectangleData } from "fusion/primitives/Rectangle";
import { Note, NoteData } from "@/model/Note";
import { pamet } from "@/core/facade";
import { MediaItem } from "fusion/model/MediaItem";
import { PametRoute } from "@/services/routing/route";
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
            metadata: {},
            tags: []
        }
        noteData = Object.assign(noteData, props);
        return new CardNote(noteData);
    }
    static createInternalLinkNote(page: Page): CardNote {
        let id = getEntityId();
        let currentTimestamp = timestamp(currentTime());

        let note = new CardNote({
            id: id,
            parent_id: page.id,
            content: {
                text: page.name,
                url: new PametRoute({ pageId: page.id }).toProjectScopedURI(),
            },
            geometry: [0, 0, 200, 100],
            style: {
                background_color_role: 'primary',
                color_role: 'onPrimary',
            },
            created: currentTimestamp,
            modified: currentTimestamp,
            metadata: {},
            tags: []
        });
        return note;
    }

    layout(): CardNoteLayout {
        let noteRect = this.rect();
        let hasText = this.content.text;
        let hasImage = this.content.image_id;

        let textArea: Rectangle | undefined;
        let imageArea: Rectangle | undefined;

        if (hasText && !hasImage) {
            textArea = noteRect;
        } else if (!hasText && hasImage) {
            imageArea = noteRect;
        } else if (hasText && hasImage) {
            let imageAspectRatio = 1;
            const mediaItem = pamet.findOne({ id: this.content.image_id }) as MediaItem;
            if (mediaItem && mediaItem.width > 0 && mediaItem.height > 0) {
                imageAspectRatio = mediaItem.width / mediaItem.height;
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
                    noteRect.x + imageArea.width(),
                    noteRect.y,
                    noteSize.x - imageArea.width(),
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
                    noteRect.y + imageArea.height(),
                    noteSize.x,
                    noteSize.y - imageArea.height()
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

    internalLinkRoute(): PametRoute | undefined {
        let url = this.content.url
        if (url === undefined) {
            return undefined
        }
        let route = PametRoute.fromUrl(url)
        if (route.isInternal && route.pageId !== undefined) {
            return route
        }
    }
    get hasInternalPageLink(): boolean {  // If refactoring change the index configs for Pamet
        return this.internalLinkRoute() !== undefined
    }
    get hasExternalLink(): boolean | undefined {  // If refactoring change the index configs for Pamet
        return !!(this.content.url && !this.hasInternalPageLink)
    }
}
