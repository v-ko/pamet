import { Color } from "../util";
import { Rectangle } from "../util/Rectangle";

import { entityType } from "../fusion/libs/Entity";
import { PageChild, PageChildData } from "./PageChild";
import { Point2D } from "../util/Point2D";
import { NOTE_MARGIN } from "../constants";
import { ArrowAnchorType } from "./Arrow";

export interface NoteContent {
    text?: string;
    url?: string;
    image_url?: string;
    local_image_url?: string;
}
export interface NoteStyle {
    color: Color;
    background_color: Color;
}

export interface NoteMetadata {
}
export interface NoteData extends PageChildData {
    own_id: string;
    content: NoteContent;
    geometry: [number, number, number, number];
    style: NoteStyle;
    created: string;
    modified: string;
    metadata: NoteMetadata;
    tags: string[];
}

@entityType
export class Note extends PageChild<NoteData> implements NoteData {

    get rect(): Rectangle {
        return new Rectangle(...this._data.geometry);
    }
    get geometry(): [number, number, number, number] {
        return this._data.geometry;
    }

    // Data access properties
    get created(): string {
        return this._data.created;
    }
    get modified(): string {
        return this._data.modified;
    }
    get metadata(): NoteMetadata {
        return this._data.metadata;
    }
    get tags(): string[] {
        return this._data.tags;
    }
    get style(): NoteStyle {
        return this._data.style;
    }
    get content(): NoteContent {
        return this._data.content;
    }

    textRect(forSize: Point2D | null = null): Rectangle {
        let size: Point2D;
        if (forSize !== null) {
            size = forSize;
        } else {
            size = this.rect.size();
        }
        size = size.subtract(new Point2D(2 * NOTE_MARGIN, 2 * NOTE_MARGIN));
        return new Rectangle(NOTE_MARGIN, NOTE_MARGIN, size.x, size.y);
    }

    arrowAnchor(anchorType: ArrowAnchorType): Point2D {
        const rect = this.rect;
        switch (anchorType) {
            case ArrowAnchorType.MID_LEFT:
                return rect.topLeft().add(new Point2D(0, rect.height() / 2));
            case ArrowAnchorType.TOP_MID:
                return rect.topLeft().add(new Point2D(rect.width() / 2, 0));
            case ArrowAnchorType.MID_RIGHT:
                return rect.topRight().add(new Point2D(0, rect.height() / 2));
            case ArrowAnchorType.BOTTOM_MID:
                return rect.bottomLeft().add(new Point2D(rect.width() / 2, 0));
            default:
                throw new Error('Invalid anchor type');
        }
    }

}
