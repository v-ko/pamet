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
import { Note } from "@/model/Note";
import { Arrow } from "@/model/Arrow";
import { MediaItem } from "fusion/model/MediaItem";
import { NoteViewState } from "@/components/note/NoteViewState";
import { ArrowViewState } from "@/components/arrow/ArrowViewState";
import { dumpToDict, getEntityId, loadFromDict } from "fusion/model/Entity";
import { WebAppState } from "@/containers/app/WebAppState";
import { PageViewState } from "@/components/page/PageViewState";

const log = getLogger('PageProcedures');

type MediaOp =
  | { type: 'restore'; media: MediaItem; newParentId: string }
  | { type: 'duplicate'; media: MediaItem; newParentId: string };

function preparePasteTransform(appState: WebAppState, state: PageViewState, relativeTo: Point2D) {
    const clipboard = appState.clipboard;
    const pageId = state.page().id;

    // Split clipboard content by type
    const clipboardNotes: Note[] = [];
    const clipboardArrows: Arrow[] = [];
    const clipboardMedia: MediaItem[] = [];
    for (const e of clipboard) {
      if (e instanceof Note) clipboardNotes.push(e);
      else if (e instanceof Arrow) clipboardArrows.push(e);
      else if (e instanceof MediaItem) clipboardMedia.push(e);
    }

    // Build id remap tables (preserve ids when no collision)
    const noteIdMap = new Map<string, string>();   // oldNoteId -> newNoteId
    const arrowIdMap = new Map<string, string>();  // oldArrowId -> newArrowId

    function nextFreeIdOrSame(originalId: string): string {
      const existing = pamet.findOne({ id: originalId });
      return existing ? getEntityId() : originalId;
    }

    // Compute snapped paste offset once
    const pasteOffset = util.snapVectorToGrid(relativeTo);

    // Notes: assign ids/parent, position
    const notesToInsert: Note[] = [];
    for (const src of clipboardNotes) {
      const targetId = nextFreeIdOrSame(src.id);
      noteIdMap.set(src.id, targetId);

      // Deep clone via dump/load, then set identity
      const noteData = dumpToDict(src);
      noteData.id = targetId;
      noteData.parent_id = pageId;
      const note = loadFromDict(noteData) as Note;

      // Position = pasteOffset + storedRelativeTopLeft (already relative in clipboard)
      const rect = note.rect();
      rect.setTopLeft(pasteOffset.add(rect.topLeft()));
      rect.setTopLeft(util.snapVectorToGrid(rect.topLeft()));
      note.setRect(rect);

      notesToInsert.push(note);
    }

    // Arrows: assign ids/parent, offset geometry, remap anchors
    const arrowsToInsert: Arrow[] = [];
    for (const src of clipboardArrows) {
      const targetId = nextFreeIdOrSame(src.id);
      arrowIdMap.set(src.id, targetId);

      const arrowData = dumpToDict(src);
      arrowData.id = targetId;
      arrowData.parent_id = pageId;
      const arrow = loadFromDict(arrowData) as Arrow;

      // Offset absolute endpoints by paste offset
      if (arrow.headPositionIsAbsolute && arrow.headPoint) {
        arrow.headPoint = arrow.headPoint.add(pasteOffset);
      }
      if (arrow.tailPositionIsAbsolute && arrow.tailPoint) {
        arrow.tailPoint = arrow.tailPoint.add(pasteOffset);
      }

      // Offset midpoints by paste offset
      const mids = arrow.midPoints().map(p => p.add(pasteOffset));
      arrow.replaceMidpoints(mids);

      // Remap anchors to new note ids (if remapped)
      if (arrow.headNoteId) {
        const newHeadId = noteIdMap.get(arrow.headNoteId) || arrow.headNoteId;
        (arrow as any)._data.head.noteAnchorId = newHeadId;
      }
      if (arrow.tailNoteId) {
        const newTailId = noteIdMap.get(arrow.tailNoteId) || arrow.tailNoteId;
        (arrow as any)._data.tail.noteAnchorId = newTailId;
      }

      arrowsToInsert.push(arrow);
    }

    // Media operations plan:
    // For each CardNote in clipboard with an image_id, decide whether to restore (if the media
    // is not present in the FDS → it was cut) or duplicate (if present → it was copied).
    const mediaIndexById = new Map<string, MediaItem>();
    for (const m of clipboardMedia) mediaIndexById.set(m.id, m);

    const mediaOps: MediaOp[] = [];
    for (const srcNote of clipboardNotes) {
      if (srcNote instanceof CardNote && srcNote.content.image_id) {
        const media = mediaIndexById.get(srcNote.content.image_id);
        const newParentId = noteIdMap.get(srcNote.id) || srcNote.id;
        if (!media) {
          log.warning('Clipboard media for note not found; will drop image ref on paste', srcNote.id, srcNote.content.image_id);
          continue;
        }
        const mediaStillInFDS = !!pamet.findOne({ id: media.id });
        if (mediaStillInFDS) {
          mediaOps.push({ type: 'duplicate', media, newParentId });
        } else {
          mediaOps.push({ type: 'restore', media, newParentId });
        }
      }
    }

    // Return transformed entities and media ops plan
    // @ts-ignore
    return { notesToInsert, arrowsToInsert, mediaOps };
  }

export async function pasteInternal(
    appState: WebAppState,
    state: PageViewState,
    relativeTo: Point2D
): Promise<void> {
    const clipboard = appState.clipboard;
    if (!clipboard || clipboard.length === 0) {
        log.info('pasteInternal called with empty clipboard');
        return;
    }

    // Prepare transformed notes/arrows and a media ops plan
    const { notesToInsert, arrowsToInsert, mediaOps } = preparePasteTransform(appState, state, relativeTo);

    const mediaToInsert: MediaItem[] = [];
    const newMediaIdByNewNoteId = new Map<string, string>(); // newNoteId -> newMediaId

    const currentProjectId = pamet.appViewState.currentProjectId;
    if (!currentProjectId) {
        throw new Error('No current project set for pasteInternal');
    }

    // Execute media plan: ensure blobs are present by duplicating or restoring
    for (const op of mediaOps as MediaOp[]) {
        if (op.type === 'duplicate') {
            const ts = generateFilenameTimestamp();
            const ext = mapMimeTypeToFileExtension(op.media.mimeType);
            const imagePath = `images/pasted_image-${ts}.${ext}`;

            // Fetch original blob and create a brand-new media item under this page
            const srcBlob = await pamet.storageService.getMedia(currentProjectId, op.media.id, op.media.contentHash);
            const created = await pamet.addMediaToStore(srcBlob, imagePath, state.page().id);

            mediaToInsert.push(created);
            newMediaIdByNewNoteId.set(op.newParentId, created.id);
        } else if (op.type === 'restore') {  // Is restored by the media service automatically at commit time
            mediaToInsert.push(op.media);
            newMediaIdByNewNoteId.set(op.newParentId, op.media.id);
        }
    }

    // Update notes to point to their new media ids (if any)
    for (const note of notesToInsert) {
        if (note instanceof CardNote) {
            const mappedMediaId = newMediaIdByNewNoteId.get(note.id);
            if (mappedMediaId) {
                note.content.image_id = mappedMediaId;
            } else if (note.content.image_id) {
                delete (note as any)._data.content.image_id;
            }
        }
    }

    // Insert via action to update FDS and View state in one place
    pageActions.pasteInternalAddElements(appState, state, notesToInsert, arrowsToInsert, mediaToInsert);
}

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
        const mediaItem = await pamet.addMediaToStore(finalImageBlob, imagePath, pageId);
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


export async function cutInternal(
    appState: WebAppState,
    state: PageViewState,
    relativeTo: Point2D
): Promise<void> {
    // Build selection sets
    const selectedNotes: Note[] = [];
    const selectedArrowsDirect: Arrow[] = [];
    for (const elementVS of state.selectedElementsVS) {
        if (elementVS instanceof NoteViewState) {
            selectedNotes.push(elementVS.note());
        } else if (elementVS instanceof ArrowViewState) {
            selectedArrowsDirect.push(elementVS.arrow());
        }
    }

    if (selectedNotes.length === 0 && selectedArrowsDirect.length === 0) {
        log.warning('cutInternal called with no selected elements');
        appState.clipboard = [];
        return;
    }

    const pageId = state.page().id;
    const selectedNoteIds = new Set<string>(selectedNotes.map(n => n.id));

    // 1) Prepare clipboard payload: notes/arrows with relative coords + trashed media for image notes
    const clipboardEntities: (Note | Arrow | MediaItem)[] = [];

    // Clone notes and shift to relative coordinates
    for (const note of selectedNotes) {
        const cloned = note.copy() as Note;
        const rect = cloned.rect();
        rect.setTopLeft(rect.topLeft().subtract(relativeTo));
        cloned.setRect(rect);
        clipboardEntities.push(cloned);
    }

    // Decide which arrows to include:
    // - Any arrow explicitly selected by the user
    // - Any arrow whose endpoints are both within the selected notes set
    const arrowIdsIncluded = new Set<string>();
    const arrowsToInclude: Arrow[] = [];

    for (const a of selectedArrowsDirect) {
        if (!arrowIdsIncluded.has(a.id)) {
            arrowsToInclude.push(a);
            arrowIdsIncluded.add(a.id);
        }
    }
    for (const arrow of pamet.arrows({ parentId: pageId })) {
        const headOk = !arrow.headNoteId || selectedNoteIds.has(arrow.headNoteId);
        const tailOk = !arrow.tailNoteId || selectedNoteIds.has(arrow.tailNoteId);
        if (headOk && tailOk && !arrowIdsIncluded.has(arrow.id)) {
            arrowsToInclude.push(arrow);
            arrowIdsIncluded.add(arrow.id);
        }
    }

    // Clone arrows and shift absolute geometry to relative coordinates
    for (const src of arrowsToInclude) {
        const cloned = src.copy() as Arrow;
        if (cloned.headPositionIsAbsolute && cloned.headPoint) {
            cloned.headPoint = cloned.headPoint.subtract(relativeTo);
        }
        if (cloned.tailPositionIsAbsolute && cloned.tailPoint) {
            cloned.tailPoint = cloned.tailPoint.subtract(relativeTo);
        }
        const mids = cloned.midPoints().map(p => p.subtract(relativeTo));
        cloned.replaceMidpoints(mids);
        clipboardEntities.push(cloned);
    }

    // 2) Collect associated media for clipboard and schedule entity removal (blob handling is backend-managed)
    const mediaToRemove: MediaItem[] = [];
    for (const note of selectedNotes) {
        if (note instanceof CardNote && note.content.image_id) {
            const mediaItem = pamet.mediaItem(note.content.image_id);
            if (!mediaItem) {
                log.warning(`Cut: media item ${note.content.image_id} not found for note ${note.id}`);
                continue;
            }
            clipboardEntities.push(mediaItem); // Keep metadata on clipboard
            mediaToRemove.push(mediaItem);     // Remove entity via action; storage will trash blob on commit
        }
    }

    // Place payload on internal clipboard
    appState.clipboard = clipboardEntities;

    // 3) Compute elements to remove from the document
    // Notes: exactly the selected notes
    const notesForRemoval = selectedNotes;

    // Arrows: selected arrows + arrows connected to notesForRemoval
    const arrowsForRemoval: Arrow[] = [...selectedArrowsDirect];
    const arrowIdsForRemoval = new Set<string>(selectedArrowsDirect.map(a => a.id));
    for (const arrow of pamet.arrows({ parentId: pageId })) {
        if (
            (arrow.tailNoteId && selectedNoteIds.has(arrow.tailNoteId)) ||
            (arrow.headNoteId && selectedNoteIds.has(arrow.headNoteId))
        ) {
            if (!arrowIdsForRemoval.has(arrow.id)) {
                arrowsForRemoval.push(arrow);
                arrowIdsForRemoval.add(arrow.id);
            }
        }
    }

    // 4) Apply removals via sync action (does not touch media blobs; media already moved to trash)
    pageActions.cutRemoveElements(appState as any, state, notesForRemoval, arrowsForRemoval, mediaToRemove as any);
}
