import { MediaItem, MediaItemData } from "../model/MediaItem";

// Global cleanup parameters
export const MAX_VERSIONS_PER_MEDIA_ITEM = 5; // Maximum versions to keep in trash per media item
export const TRASHED_ITEM_EXPIRY_TIME = 7 * 24 * 60 * 60 * 1000; // 1 week in milliseconds

export class MediaItemExistsInPathError extends Error {
  constructor(path: string) {
    super(`Media item already exists at path: ${path}`);
    this.name = 'MediaItemExistsInPathError';
  }
}

export interface MediaStoreAdapter {
  addMedia: (blob: Blob, path: string) => Promise<MediaItemData>;
  getMedia: (mediaId: string, mediaHash: string) => Promise<Blob>;
  removeMedia: (mediaItem: MediaItem) => Promise<void>;
}
