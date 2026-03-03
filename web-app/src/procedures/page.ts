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
import { ImageItem } from "fusion/model/ImageItem";
import { NoteViewState } from "@/components/note/NoteViewState";
import { ArrowViewState } from "@/components/arrow/ArrowViewState";
import { dumpToDict, getEntityId, loadFromDict } from "fusion/model/Entity";
import { WebAppState } from "@/containers/app/WebAppState";
import { PageViewState } from "@/components/page/PageViewState";

const log = getLogger('PageProcedures');

function preparePasteTransform(appState: WebAppState, state: PageViewState, relativeTo: Point2D) {
    const clipboard = appState.clipboard;
    const pageId = state.page().id;

    // Split clipboard content by type (ImageItems on clipboard are ignored —
    // FileItems are project-level and already in the store; notes just keep their image_id)
    const clipboardNotes: Note[] = [];
    const clipboardArrows: Arrow[] = [];
    for (const e of clipboard) {
      if (e instanceof Note) clipboardNotes.push(e);
      else if (e instanceof Arrow) clipboardArrows.push(e);
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

    // Notes: assign ids/parent, position.
    // image_id references are preserved — the pasted note points to the same FileItem.
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

    return { notesToInsert, arrowsToInsert };
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

    // Prepare transformed notes/arrows (FileItems are shared — notes keep their image_id)
    const { notesToInsert, arrowsToInsert } = preparePasteTransform(appState, state, relativeTo);

    // Cross-project paste: if clipboard came from a different project,
    // copy blobs into the current project and remap image_ids on pasted notes.
    const currentProjectId = appState.currentProjectId;
    const sourceProjectId = appState.clipboardProjectId;
    const newImageItems: ImageItem[] = [];
    if (currentProjectId && sourceProjectId && sourceProjectId !== currentProjectId) {
        // Collect ImageItems from clipboard for lookup
        const clipboardImageItems = new Map<string, ImageItem>();
        for (const e of clipboard) {
            if (e instanceof ImageItem) {
                clipboardImageItems.set(e.id, e);
            }
        }

        if (clipboardImageItems.size > 0) {
            // Show loading dialog for cross-project file copy
            appActions.updateSystemDialogState(appState, {
                title: 'Copying files from source project...',
            });

            const sourceConfig = pamet.projectStorageConfig(sourceProjectId);
            try {
                // Temporarily load the source project for file access
                await pamet.storageService.loadProject(sourceProjectId, sourceConfig);

                const imageIdRemap = new Map<string, string>(); // old image_id -> new image_id
                for (const note of notesToInsert) {
                    if (note instanceof CardNote && note.content.image_id) {
                        const oldImageId = note.content.image_id;
                        if (imageIdRemap.has(oldImageId)) {
                            note.content.image_id = imageIdRemap.get(oldImageId)!;
                            continue;
                        }
                        const sourceImageItem = clipboardImageItems.get(oldImageId);
                        if (!sourceImageItem) {
                            log.warning(`Cross-project paste: ImageItem ${oldImageId} not on clipboard`);
                            continue;
                        }
                        try {
                            const blob = await pamet.storageService.getFile(
                                sourceProjectId, sourceImageItem.id, sourceImageItem.contentHash
                            );
                            const newImageItem = await pamet.addFileToStore(
                                blob, sourceImageItem.path, '',
                                { width: sourceImageItem.width, height: sourceImageItem.height, size: blob.size, mimeType: blob.type }
                            );
                            imageIdRemap.set(oldImageId, newImageItem.id);
                            note.content.image_id = newImageItem.id;
                            newImageItems.push(newImageItem);
                            log.info(`Cross-project paste: remapped image ${oldImageId} -> ${newImageItem.id}`);
                        } catch (err) {
                            log.error(`Cross-project paste: failed to copy file for image ${oldImageId}`, err);
                        }
                    }
                }
            } finally {
                // Unload only if it was successfully loaded (ref count > 0)
                await pamet.storageService.unloadProject(sourceProjectId).catch(
                    (e) => log.error('Error unloading source project after paste', e)
                );
                appActions.updateSystemDialogState(appState, null);
            }
        }
    }

    // Insert via action to update FDS and View state in one place
    pageActions.pasteInternalAddElements(appState, state, notesToInsert, arrowsToInsert, newImageItems);
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
        const currentProjectId = pamet.appViewState.currentProjectId;
        if (!currentProjectId) {
            throw new Error('No current project set when pasting image');
        }
        const imageItem = await pamet.addFileToStore(finalImageBlob, imagePath, '', { width, height, size: finalImageBlob.size, mimeType: finalImageBlob.type });
        note.content.image_id = imageItem.id;

        // Configure note position and size
        let rect = note.rect();
        rect.setTopLeft(position);
        let size = util.snapVectorToGrid(minimalNonelidedSize(note));
        rect.setSize(size);
        note.setRect(rect);

        pageActions.pasteSpecialAddElements([note], [imageItem]);

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
        appState.clipboardProjectId = null;
        return;
    }

    const pageId = state.page().id;
    const selectedNoteIds = new Set<string>(selectedNotes.map(n => n.id));

    // 1) Prepare clipboard payload: notes/arrows with relative coords + trashed media for image notes
    const clipboardEntities: (Note | Arrow | ImageItem)[] = [];

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

    // 2) Collect associated image items for clipboard reference (for display/re-reference on paste)
    for (const note of selectedNotes) {
        if (note instanceof CardNote && note.content.image_id) {
            const imageItem = pamet.imageItem(note.content.image_id);
            if (!imageItem) {
                log.warning(`Cut: image item ${note.content.image_id} not found for note ${note.id}`);
                continue;
            }
            clipboardEntities.push(imageItem); // Keep metadata on clipboard for reference
        }
    }

    // Place payload on internal clipboard
    appState.clipboard = clipboardEntities;
    appState.clipboardProjectId = appState.currentProjectId;

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

    // 4) Apply removals — only notes and arrows. FileItems are project-level and kept intact.
    pageActions.cutRemoveElements(appState as any, state, notesForRemoval, arrowsForRemoval);
}
