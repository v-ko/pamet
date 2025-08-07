import { Rectangle } from "../util/Rectangle";

import { PametElement, PametElementData } from "./Element";
import { textRect } from "../components/note/util";
import { entityType } from "fusion/libs/Entity";

export interface NoteContent {
    text?: string;
    url?: string;
    image_id?: string;
}
export interface NoteStyle {
    color_role: string;
    background_color_role: string;
}

export interface NoteMetadata {
}
export interface NoteData extends PametElementData {
    content: NoteContent;
    geometry: [number, number, number, number];
    style: NoteStyle;
    created: string;
    modified: string;
    metadata: NoteMetadata;
    tags: string[];
}

export interface SerializedNote extends NoteData {
    type_name: string;
}

@entityType('Note') // was removed .. ? but it's needed for the inmem store search at minimum (instanceof matching)
export class Note extends PametElement<NoteData> {
    // This is only a base class, static helpers should go in the subclasses
    rect(): Rectangle {
        return new Rectangle(...this._data.geometry);
    }
    setRect(rect: Rectangle) {
        this._data.geometry = rect.data();
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
    get text(): string {
        return this._data.content.text || '';
    }
    textRect(): Rectangle {
        return textRect(this.rect());
    }
}
