/**
 * Utility functions for media operations
 */

/**
 * Extract dimensions from an image blob
 */
export async function extractImageDimensions(blob: Blob): Promise<{ width: number; height: number }> {
    // DEBUG: Log context information
    console.log('[DEBUG] extractImageDimensions called in context:', {
        hasImage: typeof Image !== 'undefined',
        hasCreateObjectURL: typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function',
        hasOffscreenCanvas: typeof OffscreenCanvas !== 'undefined',
        hasImageBitmap: typeof createImageBitmap === 'function',
        isServiceWorker: typeof self !== 'undefined' && typeof window === 'undefined',
        blobType: blob.type,
        blobSize: blob.size
    });

    // Check if we're in a service worker context where Image is not available
    if (typeof Image === 'undefined') {
        console.log('[DEBUG] Image constructor not available, attempting service worker compatible approach');

        // Try using ImageBitmap API which is available in service workers
        if (typeof createImageBitmap === 'function') {
            try {
                console.log('[DEBUG] Attempting ImageBitmap approach');
                const imageBitmap = await createImageBitmap(blob);
                const dimensions = { width: imageBitmap.width, height: imageBitmap.height };
                console.log('[DEBUG] ImageBitmap dimensions extracted:', dimensions);
                imageBitmap.close(); // Clean up
                return dimensions;
            } catch (error) {
                console.error('[DEBUG] ImageBitmap approach failed:', error);
            }
        }

        // Fallback: return default dimensions and log the issue
        console.warn('[DEBUG] No service worker compatible image dimension extraction available, returning default dimensions');
        return { width: 0, height: 0 };
    }

    // Original Image-based approach for main thread
    console.log('[DEBUG] Using Image constructor approach (main thread)');
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            const dimensions = { width: img.naturalWidth, height: img.naturalHeight };
            console.log('[DEBUG] Image dimensions extracted:', dimensions);
            resolve(dimensions);
            URL.revokeObjectURL(img.src); // Clean up the object URL
        };
        img.onerror = () => {
            console.error('[DEBUG] Image load error');
            URL.revokeObjectURL(img.src); // Clean up the object URL
            reject(new Error('Failed to load image for dimension extraction'));
        };
        img.src = URL.createObjectURL(blob);
    });
}

/**
 * Generate a SHA-256 content hash for a blob
 */
export async function generateContentHash(blob: Blob): Promise<string> {
    const arrayBuffer = await blob.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
