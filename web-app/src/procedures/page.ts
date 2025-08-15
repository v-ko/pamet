import { Point2D } from "fusion/primitives/Point2D";
import { minimalNonelidedSize } from "@/components/note/note-dependent-utils";
import * as util from "@/util";
import { pamet } from "@/core/facade";
import { pageActions } from "@/actions/page";
import { appActions } from "@/actions/app";
import { generateFilenameTimestamp } from "fusion/util/base";
import { getLogger } from "fusion/logging";
import { AGU, MAX_IMAGE_DIMENSION_FOR_COMPRESSION } from "@/core/constants";
import { ImageVerdict, determineConversionPreset, shouldCompressImage } from "@/core/policies";
import { convertImage, extractImageDimensions } from "fusion/util/media";
import { mapMimeTypeToFileExtension } from "fusion/util/base";
import { CardNote } from "@/model/CardNote";

const log = getLogger('PageProcedures');

/**
 * Handle pasting an image from clipboard data.
 * Applies compression policies, creates a unique path for the image,
 * and adds it to the media store.
 *
 * @param pageId - The ID of the page where the image should be pasted
 * @param position - The position where the image note should be created
 * @param imageBlob - The image blob from clipboard
 * @param mimeType - The MIME type of the image
 * @returns The position for the next paste item
 */
export async function createNoteWithImageFromBlob(
    pageId: string,
    position: Point2D,
    imageBlob: Blob
): Promise<Point2D> {
    let finalImageBlob = imageBlob;
    let note;

    try {
        const { width, height } = await extractImageDimensions(imageBlob);
        const verdict = shouldCompressImage({ width, height, size: imageBlob.size, mimeType: imageBlob.type });

        if (verdict === ImageVerdict.Reject) {
            const errorText = `Image is too large to process (${width}x${height}). Maximum allowed is ${MAX_IMAGE_DIMENSION_FOR_COMPRESSION}px.`;
            log.error(errorText, "the image will be skipped.");
            return position; // Skip item, return original position
        }

        if (verdict === ImageVerdict.Compress) {
            const preset = determineConversionPreset(imageBlob.type);
            const imageFile = new File([imageBlob], "pasted_image", { type: imageBlob.type });
            finalImageBlob = await convertImage(imageFile, preset);
        }

        const timestamp = generateFilenameTimestamp();
        const extension = mapMimeTypeToFileExtension(finalImageBlob.type);
        const imagePath = `images/pasted_image-${timestamp}.${extension}`;

        note = CardNote.createNew({pageId: pageId});
        const mediaItem = await pamet.addMediaToStore(finalImageBlob, imagePath, note.id);
        note.content.image_id = mediaItem.id;

        // Configure note position and size
        let rect = note.rect();
        rect.setTopLeft(position);
        let size = util.snapVectorToGrid(minimalNonelidedSize(note));
        rect.setSize(size);
        note.setRect(rect);

        pageActions.pasteSpecialAddElements([note], [mediaItem]);

        return position.add(new Point2D([0, size.y + AGU]));

    } catch (error) {
        log.error('Error processing pasted image:', error, 'The item will be skipped.');
        return position; // On any error, skip the item and return the original position
    }
}

/**
 * Handle pasting multiple clipboard items (text, images, etc.) at a position.
 *
 * @param pageId - The ID of the page where items should be pasted
 * @param position - The starting position where items should be pasted
 * @param pasteData - Array of clipboard items to paste
 * @returns Promise that resolves when all items are pasted
 */
export async function pasteSpecial(
    pageId: string,
    position: Point2D,
    pasteData: util.ClipboardItem[]
): Promise<void> {

    appActions.updateSystemDialogState(pamet.appViewState, {title: 'Pasting content', showAfterUnixTime: Date.now() + 500});

    try {
        let pasteAt = position;
        const totalItems = pasteData.length;
        let itemsProcessed = 0;

        if (totalItems > 100) {
            let result = window.confirm(`Pasting ${totalItems} items. Are you sure?`);
            if (!result) {
                return;
            }
        }

        for (const item of pasteData) {
            itemsProcessed++;
            let taskDescription = `Processing item ${itemsProcessed} of ${totalItems}`;
            let taskProgress = (itemsProcessed / totalItems) * 100;
            appActions.updateSystemDialogState(pamet.appViewState, {taskDescription: taskDescription, taskProgress: taskProgress});
            // await new Promise(resolve => setTimeout(resolve, 1000));

            if (item.type === 'text') {
                let note = CardNote.createNew({pageId: pageId});
                note.content.text = item.text;

                let rect = note.rect();
                rect.setTopLeft(pasteAt);
                let size = util.snapVectorToGrid(minimalNonelidedSize(note));
                rect.setSize(size);
                note.setRect(rect);

                pageActions.pasteSpecialAddElements([note], []);
                pasteAt = pasteAt.add(new Point2D([0, size.y + AGU]));

            } else if (item.type === 'image') {
                if (item.image_blob && item.mime_type) {
                    try {
                        pasteAt = await createNoteWithImageFromBlob(pageId, pasteAt, item.image_blob);
                    } catch (error) {
                        log.error('Error pasting image:', error);
                    }
                } else {
                    log.error('Image clipboard item missing blob or mime type');
                }
            }
        }
    } finally {
        appActions.updateSystemDialogState(pamet.appViewState, null);
    }
}

