import { Entity, EntityData, entityType, getEntityId } from "fusion/libs/Entity";
import { PametRoute } from "../services/routing/route";

export interface MediaItemData extends EntityData {
    // Should have only simple types, no nested objects or arrays
    // Because it will be put into the e.g. note.content.image field
    // and we have a max nesting factor of 3 (e.g. note.content.image.width)
    // for entities
    path: string;  // For project organization and FS storage (e.g. path relative to the project root and a name for the item)
    contentHash: string;  // Updated on content edit, enables id persistence through edits
    width: number;  // For rendering placeholders and doing geometry calculations
    height: number;  // For audio those are 0. That's the only rendundancy. Better to have that than a complex model
    mimeType: string;  // MIME type of the image (e.g. 'image/jpeg', 'image/png')
    size: number;  // Size of the image in bytes
    timeDeleted?: number;  // Timestamp when item was deleted (undefined = not deleted). We keep a trash bin for undo/redo functionality
}

@entityType('MediaItem')
export class MediaItem extends Entity<MediaItemData> {
    constructor(data: MediaItemData) {
        super(data);
    }

get parentId(): string {
        // MediaItems are project-level entities, so they don't have a specific parent
        // Return empty string to indicate no parent
        return '';
    }

    // Data access properties
    get path(): string {
        return this._data.path;
    }

    get contentHash(): string {
        return this._data.contentHash;
    }

    get width(): number {
        return this._data.width;
    }

    get height(): number {
        return this._data.height;
    }

    get mimeType(): string {
        return this._data.mimeType;
    }

    get size(): number {
        return this._data.size;
    }

    get timeDeleted(): number {
        if (!this.isDeleted) {
            throw new Error("MediaItem is not deleted");
        }
        return this._data.timeDeleted!;
    }

    get isDeleted(): boolean {
        return this._data.timeDeleted !== undefined;
    }

    // Mark this MediaItem as deleted
    markDeleted(): void {
        this._data.timeDeleted = Date.now();
    }

    // Get the project-scoped URL for this media item
    pametRoute(userId: string, projectId: string): PametRoute {
        let route = new PametRoute();
        route.mediaItemId = this.id;
        route.mediaItemContentHash = this.contentHash;
        route.userId = userId;
        route.projectId = projectId;
        return route
    }

    // Static factory method for creating new MediaItems
    static create(data: Omit<MediaItemData, 'id'>): MediaItem {
        return new MediaItem({
            id: getEntityId(),
            ...data
        });
    }
}
