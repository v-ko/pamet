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
    const response = new Response(blob, {
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
  // // Method to set up fetch interception (service worker only)
  // private setupFetchInterception(): void {
  //   // Check if we're running in a service worker context
  //   // Use the same check pattern as StorageService.inWorker
  //   if (typeof self === 'undefined') {
  //     throw new Error('CacheMediaStoreAdapter can only be used in a service worker context. Fetch interception requires service worker capabilities.');
  //   }

  //   // Check if fetch event interception is available
  //   if (typeof self.addEventListener !== 'function') {
  //     throw new Error('Service worker fetch event interception is not available. Cannot set up media cache interception.');
  //   }

  //   // Set up fetch event listener for media requests
  //   const handleFetch = (event: Event) => {
  //     const fetchEvent = event as FetchEvent;
  //     const url = fetchEvent.request.url;

  //     log.info(`Intercepting fetch request for URL: ${url}`);


  //     // Only intercept /media/item/ requests for this specific project
  //     if (url.includes('/media/item/')) {
  //       // Parse the URL to check if it's for this project
  //       const route = PametRoute.fromUrl(url);
  //       if (route.projectId === this._projectId) {
  //         fetchEvent.respondWith(this.handleMediaRequest(fetchEvent.request));
  //       }
  //     }
  //   };

  //   // Add the fetch event listener
  //   self.addEventListener('fetch', handleFetch);
  //   log.info(`Set up fetch interception for media requests in service worker for project: ${this._projectId}`);
  // }

  // // Handle media requests in service worker
  // private async handleMediaRequest(request: Request): Promise<Response> {
  //   try {
  //     // Parse the request URL using PametRoute
  //     const route = PametRoute.fromUrl(request.url);

  //     if (!route.mediaItemId) {
  //       log.warning(`Invalid media URL format: ${request.url}`);
  //       return new Response('Invalid media URL format', {
  //         status: 400,
  //         statusText: 'Bad Request',
  //         headers: { 'Content-Type': 'text/plain' }
  //       });
  //     }

  //     // Create relative cache key for lookup
  //     const cacheKey = this._getCacheKey(route.mediaItemId, route.mediaItemContentHash || '');

  //     // Try to get from cache
  //     const cachedResponse = await this.cache.match(cacheKey);

  //     if (cachedResponse) {
  //       log.info(`Serving cached media: ${cacheKey} for project: ${this._projectId}`);
  //       return cachedResponse.clone();
  //     }

  //     // If not in cache, return 404 (no network fallback as per user feedback)
  //     log.warning(`Media not found in cache: ${cacheKey} for project: ${this._projectId}`);
  //     return new Response('Media not found', {
  //       status: 404,
  //       statusText: 'Not Found',
  //       headers: { 'Content-Type': 'text/plain' }
  //     });
  //   } catch (error) {
  //     log.error('Error handling media request:', error);
  //     // Return a 404 response if everything fails
  //     return new Response('Media not found', {
  //       status: 404,
  //       statusText: 'Not Found',
  //       headers: { 'Content-Type': 'text/plain' }
  //     });
  //   }
  // }
}
