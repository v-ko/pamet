import { getLogger } from "fusion/logging";
import { MediaStoreAdapter } from "./MediaStoreAdapter";
import { MediaItem, MediaItemData } from "../model/MediaItem";
import { extractImageDimensions, generateContentHash } from "../util/media";

const log = getLogger('InMemoryMediaStoreAdapter');

export class InMemoryMediaStoreAdapter implements MediaStoreAdapter {
  private _media: Map<string, Blob> = new Map();


  private _getUniqueUri(path: string): string {
    let uri = this._generateUri(path);
    let counter = 1;

    // Check if a URI with this path already exists
    while (this._media.has(uri)) {
      // Extract name and extension from path
      const lastDotIndex = path.lastIndexOf('.');
      const name = lastDotIndex !== -1 ? path.substring(0, lastDotIndex) : path;
      const extension = lastDotIndex !== -1 ? path.substring(lastDotIndex) : '';

      // Add counter to path
      const newPath = `${name}_${counter}${extension}`;
      uri = this._generateUri(newPath);
      counter++;
    }

    return uri;
  }

  private _generateUri(path: string): string {
    // Ensure path starts with /
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `project:/media${normalizedPath}`;
  }

  async addMedia(blob: Blob, path: string): Promise<MediaItemData> {
    // Generate a unique URI based on the path
    const uri = this._getUniqueUri(path);

    // Store the blob
    this._media.set(uri, blob);
    log.info(`Added media: ${uri}`);

    // Extract image dimensions if it's an image
    let width = 0;
    let height = 0;

    if (blob.type.startsWith('image/')) {
      try {
        const dimensions = await extractImageDimensions(blob);
        width = dimensions.width;
        height = dimensions.height;
      } catch (error) {
        log.warning('Failed to extract image dimensions:', error);
      }
    }

    // Generate content hash
    const contentHash = await generateContentHash(blob);

    // Create the MediaItem
    const mediaItem = MediaItem.create({
      path: uri,
      contentHash,
      width,
      height,
      mimeType: blob.type,
      size: blob.size,
      timeDeleted: undefined
    });

    return mediaItem.data(); // Return the data instead of the MediaItem instance
  }

  async getMedia(mediaId: string, mediaHash: string): Promise<Blob> {
    // Reconstruct the path from mediaId (which should be the full path)
    const blob = this._media.get(mediaId);
    if (!blob) {
      log.error(`Media not found: ${mediaId}`);
      throw new Error(`Media not found: ${mediaId}`);
    }
    return blob;
  }

  async removeMedia(mediaItem: MediaItem): Promise<void> {
    // Mark the mediaItem as deleted
    mediaItem.markDeleted();

    if (!this._media.has(mediaItem.path)) {
      log.warning(`Attempted to remove non-existent media: ${mediaItem.path}`);
      return;
    }

    this._media.delete(mediaItem.path);
    log.info(`Removed media: ${mediaItem.path}`);
  }

}
