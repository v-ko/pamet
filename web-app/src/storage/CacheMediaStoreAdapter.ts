import { getLogger } from "fusion/logging";
import { MediaStoreAdapter } from "./MediaStoreAdapter";
import { MediaItem, MediaItemData } from "../model/MediaItem";
import { extractImageDimensions, generateContentHash } from "../util/media";

const log = getLogger('CacheMediaStoreAdapter');

export class CacheMediaStoreAdapter implements MediaStoreAdapter {
  private _projectId: string;
  private _cacheName: string;
  private _cache: Cache | null = null;

  constructor(projectId: string) {
    this._projectId = projectId;
    this._cacheName = `pamet-media-${projectId}`;
  }

  async init(): Promise<void> {
    try {
      this._cache = await caches.open(this._cacheName);
      log.info(`Opened Cache API store: ${this._cacheName}`);

      // // Set up fetch interception for media requests
      // this.setupFetchInterception();
    } catch (error) {
      log.error('Failed to initialize Cache API:', error);
      throw new Error(`Failed to initialize CacheMediaStoreAdapter: ${error}`);
    }
  }

  private get cache(): Cache {
    if (!this._cache) {
      throw new Error('Cache not initialized. Call init() first.');
    }
    return this._cache;
  }

  private _getCacheKey(id: string, contentHash: string): string {
    // Create relative cache key without user/project prefix: media/item/{id}#{contentHash}
    // This makes storage user-agnostic, with security handled by cleanup on logout
    return `media/item/${id}#${contentHash}`;
  }

  async addMedia(blob: Blob, path: string): Promise<MediaItemData> {
    // Generate content hash first
    const contentHash = await generateContentHash(blob);

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

    // Create the MediaItem
    const mediaItem = MediaItem.create({
      path: path, // Store relative path (e.g. "images/photo.jpg")
      contentHash,
      width,
      height,
      mimeType: blob.type,
      size: blob.size,
      timeDeleted: undefined
    });

    // Create the cache key using MediaItem ID
    const cacheKey = this._getCacheKey(mediaItem.id, contentHash);

    // Store the blob in the Cache API using the cache key
    const response = new Response(blob.slice(), {
      headers: {
        'Content-Type': blob.type,
        'Content-Length': blob.size.toString(),
        'X-Content-Hash': contentHash, // Store hash in header for reference
      }
    });

    await this.cache.put(cacheKey, response);
    log.info(`Added media to cache: ${cacheKey}`);

    return mediaItem.data(); // Return the data instead of the MediaItem instance
  }

  async getMedia(mediaId: string, mediaHash: string): Promise<Blob> {
    // Create cache key from mediaId and mediaHash
    const cacheKey = this._getCacheKey(mediaId, mediaHash);

    const response = await this.cache.match(cacheKey);

    if (!response) {
      throw new Error(`Media not found in cache: ${cacheKey}`);
    }

    return await response.blob();
  }

  async removeMedia(mediaItem: MediaItem): Promise<void> {
    // Mark the mediaItem as deleted
    mediaItem.markDeleted();

    // Create cache key from MediaItem ID and contentHash
    const cacheKey = this._getCacheKey(mediaItem.id, mediaItem.contentHash);

    const deleted = await this.cache.delete(cacheKey);

    if (deleted) {
      log.info(`Removed media from cache: ${cacheKey}`);
    } else {
      log.warning(`Media not found for deletion: ${cacheKey}`);
    }
  }


  async close(): Promise<void> {
    // Cache API doesn't need explicit closing
    this._cache = null;
    log.info(`Closed CacheMediaStoreAdapter: ${this._cacheName}`);
  }
}
