import { ColorData } from "../util";
import { Rectangle } from "../util/Rectangle";

import { PageChild, PageChildData } from "./PageChild";
import { Point2D } from "../util/Point2D";
import { ArrowAnchorType } from "./Arrow";

export interface ImageMetadata {
    url: string;
    width: number;
    height: number;
}

export interface NoteContent {
    text?: string;
    url?: string;
    // image_url?: string; // remove that
    // local_image_url?: string; //refactor that to 'image'
    image?: ImageMetadata;
}
export interface NoteStyle {
    color: ColorData;
    background_color: ColorData;
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

// @entityType('Note')
export class Note extends PageChild<NoteData> implements NoteData {
    rect(): Rectangle {
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
    arrowAnchor(anchorType: ArrowAnchorType): Point2D {
        const rect = this.rect();
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
