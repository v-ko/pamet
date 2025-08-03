import { Point2D } from "../util/Point2D";
import { TextNote } from "../model/TextNote";
import { ImageNote } from "../model/ImageNote";
import { minimalNonelidedSize } from "../components/note/note-dependent-utils";
import * as util from "../util";
import { pamet } from "../core/facade";
import { pageActions } from "../actions/page";
import { generateFilenameTimestamp } from "fusion/util";
import { getLogger } from "fusion/logging";
import { AGU } from "../core/constants";
import { MediaItem } from "../model/MediaItem";

const log = getLogger('PageProcedures');

/**
 * Handle pasting an image from clipboard data.
 * Creates a unique path for the image and adds it to the media store.
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
    // Generate unique path for the pasted image
    const timestamp = generateFilenameTimestamp();

    // Extract file extension from MIME type
    let extension = '.png'; // Default fallback
    if (mimeType === 'image/jpeg' || mimeType === 'image/jpg') {
        extension = '.jpg';
    } else if (mimeType === 'image/gif') {
        extension = '.gif';
    } else if (mimeType === 'image/webp') {
        extension = '.webp';
    } else if (mimeType === 'image/svg+xml') {
        extension = '.svg';
    } else if (mimeType === 'image/png') {
        extension = '.png';
    }

    const imagePath = `images/pasted_image-${timestamp}${extension}`;

    // Get current project
    const currentProject = pamet.appViewState.currentProject();
    if (!currentProject) {
        throw Error('No current project set');
    }

    let note;
    let mediaItem;

    try {
        // Add the image to the media store
        const mediaItemData = await pamet.storageService.addMedia(currentProject.id, imageBlob, imagePath);
        log.info('Successfully added pasted image:', mediaItemData.path);

        // Reconstruct MediaItem from data (since Comlink serialization strips prototype methods)
        mediaItem = new MediaItem(mediaItemData);

        // Create an ImageNote with the MediaItem
        note = ImageNote.createNew(pageId, mediaItem);

    } catch (error) {
        log.error('Error adding pasted image:', error);

        // Create an error note instead
        note = TextNote.createNew(pageId);
        note.content.text = `[Error pasting image: ${error}]`;
    }

    // Configure note position and size
    let rect = note.rect();
    rect.setTopLeft(position);
    let size = util.snapVectorToGrid(minimalNonelidedSize(note));
    rect.setSize(size);
    note.setRect(rect);

    let mediaItems = [];
    if (mediaItem) {
        mediaItems.push(mediaItem);
    }
    pageActions.pasteSpecialAddElements([note], mediaItems);

    // Return position for next item
    return position.add(new Point2D(0, size.y + AGU));
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
    let pasteAt = position;

    if (pasteData.length > 100) {
        let result = window.confirm('Pasting more than 100 items. Are you sure?');
        if (!result) {
            return;
        }
    }

    // First pass: create and position all text notes
    let textNotes: TextNote[] = [];
    for (let item of pasteData) {
        if (item.type === 'text') {
            let textNote = TextNote.createNew(pageId);
            textNote.content.text = item.text;

            let rect = textNote.rect();
            rect.setTopLeft(pasteAt);
            let size = util.snapVectorToGrid(minimalNonelidedSize(textNote));
            rect.setSize(size);
            textNote.setRect(rect);

            textNotes.push(textNote);
            pasteAt = pasteAt.add(new Point2D(0, size.y + AGU)); // Move down for the next note
        }
    }

    // Bulk add all text notes
    if (textNotes.length > 0) {
        pageActions.pasteSpecialAddElements(textNotes, []);
    }

    // Second pass: handle images (these need individual processing due to async nature)
    for (let item of pasteData) {
        if (item.type === 'image') {
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
}

