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


import { IMAGE_CONVERSION_PRESET_JPG, ImageConversionPreset } from "../core/constants";


async function readFileAsDataURL(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e: any) => {
            resolve(e.target.result as string)
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

async function convertImageWithPreset(dataUrl: string, preset: ImageConversionPreset): Promise<Blob> {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            let { width, height } = img;
            const { maxWidth, maxHeight } = preset;

            if (width > height) {
                if (width > maxWidth) {
                    height = Math.round(height * (maxWidth / width));
                    width = maxWidth;
                }
            } else {
                if (height > maxHeight) {
                    width = Math.round(width * (maxHeight / height));
                    height = maxHeight;
                }
            }

            const canvas = new OffscreenCanvas(width, height);
            const ctx = canvas.getContext('2d');

            if (!ctx) {
                return reject(new Error('Could not get canvas context.'));
            }

            ctx.drawImage(img, 0, 0, width, height);

            canvas.convertToBlob({
                type: preset.mimeType,
                quality: preset.quality
            }).then(blob => {
                if (blob) {
                    resolve(blob);
                } else {
                    reject(new Error('Canvas toBlob conversion failed.'));
                }
            }).catch(reject);
        };
        img.onerror = reject;
        img.src = dataUrl;
        URL.revokeObjectURL(img.src);
    });
}


export async function convertImage(
    file: File,
    preset: ImageConversionPreset = IMAGE_CONVERSION_PRESET_JPG
): Promise<Blob> {

    if (!file.type.startsWith('image/')) {
        throw new Error('File is not an image.');
    }
    const dataUrl = await readFileAsDataURL(file);
    const blob = await convertImageWithPreset(dataUrl, preset)
    return blob;
}
