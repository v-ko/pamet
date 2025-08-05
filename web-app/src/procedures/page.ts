import { Point2D } from "../util/Point2D";
import { TextNote } from "../model/TextNote";
import { ImageNote } from "../model/ImageNote";
import { minimalNonelidedSize } from "../components/note/note-dependent-utils";
import * as util from "../util";
import { pamet } from "../core/facade";
import { pageActions } from "../actions/page";
import { appActions } from "../actions/app";
import { MediaProcessingDialogState } from "../components/system-modal-dialog/state";
import { generateFilenameTimestamp } from "fusion/util";
import { getLogger } from "fusion/logging";
import { AGU, MAX_IMAGE_DIMENSION_FOR_COMPRESSION } from "../core/constants";
import { MediaItem } from "../model/MediaItem";
import { ImageVerdict, determineConversionPreset, shouldCompressImage } from "../core/policies";
import { convertImage, extractImageDimensions } from "../util/media";
import { mapMimeTypeToFileExtension } from "../util";

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
export async function pasteImage(
    pageId: string,
    position: Point2D,
    imageBlob: Blob,
    mimeType: string
): Promise<Point2D> {
    const currentProject = pamet.appViewState.currentProject();
    if (!currentProject) {
        throw Error('No current project set');
    }

    let finalImageBlob = imageBlob;
    let note;

    try {
        const { width, height } = await extractImageDimensions(imageBlob);
        const verdict = shouldCompressImage({ width, height, size: imageBlob.size, mimeType });

        if (verdict === ImageVerdict.Reject) {
            const errorText = `Image is too large to process (${width}x${height}). Maximum allowed is ${MAX_IMAGE_DIMENSION_FOR_COMPRESSION}px.`;
            log.error(errorText, "the image will be skipped.");
            return position; // Skip item, return original position
        }

        if (verdict === ImageVerdict.Compress) {
            const preset = determineConversionPreset(mimeType);
            const imageFile = new File([imageBlob], "pasted_image", { type: mimeType });
            finalImageBlob = await convertImage(imageFile, preset);
        }

        const timestamp = generateFilenameTimestamp();
        const extension = mapMimeTypeToFileExtension(finalImageBlob.type);
        const imagePath = `images/pasted_image-${timestamp}.${extension}`;

        const mediaItemData = await pamet.storageService.addMedia(currentProject.id, finalImageBlob, imagePath);
        const mediaItem = new MediaItem(mediaItemData);
        note = ImageNote.createNew(pageId, mediaItem);

        // Configure note position and size
        let rect = note.rect();
        rect.setTopLeft(position);
        let size = util.snapVectorToGrid(minimalNonelidedSize(note));
        rect.setSize(size);
        note.setRect(rect);

        pageActions.pasteSpecialAddElements([note], [mediaItem]);

        return position.add(new Point2D(0, size.y + AGU));

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

    const dialogState = new MediaProcessingDialogState();
    dialogState.title = 'Pasting content';
    dialogState.showAfterUnixTime = Date.now() + 500;
    appActions.updateSystemDialogState(pamet.appViewState, dialogState);

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
            dialogState.taskDescription = `Processing item ${itemsProcessed} of ${totalItems}`;
            dialogState.taskProgress = (itemsProcessed / totalItems) * 100;
            // Create a new state object to ensure reactivity, since mobx might not pick up on nested property changes
            let newDialogState = Object.assign(new MediaProcessingDialogState(), dialogState);
            appActions.updateSystemDialogState(pamet.appViewState, newDialogState);
            // await new Promise(resolve => setTimeout(resolve, 1000));

            if (item.type === 'text') {
                let textNote = TextNote.createNew(pageId);
                textNote.content.text = item.text;

                let rect = textNote.rect();
                rect.setTopLeft(pasteAt);
                let size = util.snapVectorToGrid(minimalNonelidedSize(textNote));
                rect.setSize(size);
                textNote.setRect(rect);

                pageActions.pasteSpecialAddElements([textNote], []);
                pasteAt = pasteAt.add(new Point2D(0, size.y + AGU));

            } else if (item.type === 'image') {
                if (item.image_blob && item.mime_type) {
                    try {
                        pasteAt = await pasteImage(pageId, pasteAt, item.image_blob, item.mime_type);
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

