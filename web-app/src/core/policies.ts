import {
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_SIZE,
    IMAGE_CONVERSION_PRESET_JPG,
    IMAGE_CONVERSION_PRESET_PNG,
    ImageConversionPreset,
    MAX_IMAGE_DIMENSION_FOR_COMPRESSION
} from "./constants";

interface ImageInfo {
    width: number;
    height: number;
    size: number; // in bytes
    mimeType: string;
}

export enum ImageVerdict {
    Compress = 'compress',
    Reject = 'reject',
    Accept = 'accept',
}

/**
 * Determines if an image should be compressed based on its dimensions and file size.
 * It also checks if the image is too large to be processed.
 *
 * @param imageInfo - The dimensions, size, and MIME type of the image.
 * @returns An ImageVerdict enum value.
 */
export function shouldCompressImage(imageInfo: ImageInfo): ImageVerdict {
    const { width, height, size } = imageInfo;

    // Reject images that are too large to process to avoid memory issues
    if (width > MAX_IMAGE_DIMENSION_FOR_COMPRESSION || height > MAX_IMAGE_DIMENSION_FOR_COMPRESSION) {
        return ImageVerdict.Reject;
    }

    // Compress if the image exceeds the maximum dimensions or file size
    if (width > MAX_IMAGE_DIMENSION || height > MAX_IMAGE_DIMENSION || size > MAX_IMAGE_SIZE) {
        return ImageVerdict.Compress;
    }

    // Otherwise, accept the image as is
    return ImageVerdict.Accept;
}

/**
 * Determines which conversion preset to use based on the image's original MIME type.
 *
 * @param mimeType - The MIME type of the original image.
 * @returns The appropriate conversion preset (JPG for most, PNG for PNGs).
 */
export function determineConversionPreset(mimeType: string): ImageConversionPreset {
    if (mimeType === 'image/png') {
        return IMAGE_CONVERSION_PRESET_PNG;
    }
    return IMAGE_CONVERSION_PRESET_JPG;
}
