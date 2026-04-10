import type { Entity, EntityData } from 'fusion/model/Entity';
import { CardNote } from '@/model/CardNote';
import { ImageItem } from 'fusion/model/ImageItem';
import { Page } from '@/model/Page';

/** Minimal interface for querying entities — satisfied by headStore, pamet facade, etc. */
export interface EntitySource {
    find(filter: any): Generator<any>;
}

/** A pair of (original, updated) entities produced by a correctness rule. */
export interface EntityUpdateStates<T extends Entity<EntityData> = Entity<EntityData>> {
    original: T;
    updated: T;
}

/** Update content.text and page_ref.path on notes whose page_ref.id matches the renamed page. */
export function linkUpdatesForPageRename(
    store: EntitySource,
    pageId: string,
    newName: string,
    newPath: string,
): EntityUpdateStates<CardNote>[] {
    const updates: EntityUpdateStates<CardNote>[] = [];
    for (const note of store.find({ type: CardNote })) {
        const ref = (note as CardNote).content.page_ref;
        if (!ref || ref.id !== pageId) continue;
        if (note.text === newName && ref.path === newPath) continue;

        const updated = (note as CardNote).copy();
        updated.replace({
            content: {
                ...updated.content,
                text: newName,
                page_ref: { id: pageId, path: newPath },
            },
        } as any);
        updates.push({ original: note as CardNote, updated: updated as CardNote });
    }
    return updates;
}

/** Mark notes linking to a deleted page: text → "(deleted Name)", keep page_ref. */
export function linkUpdatesForPageDelete(
    store: EntitySource,
    pageId: string,
    pageName: string,
): EntityUpdateStates<CardNote>[] {
    const updates: EntityUpdateStates<CardNote>[] = [];
    const deletedText = `(deleted ${pageName})`;
    for (const note of store.find({ type: CardNote })) {
        const ref = (note as CardNote).content.page_ref;
        if (!ref || ref.id !== pageId) continue;

        const updated = (note as CardNote).copy();
        updated.replace({
            content: { ...updated.content, text: deletedText },
        } as any);
        updates.push({ original: note as CardNote, updated: updated as CardNote });
    }
    return updates;
}

/** Reassign ImageItems on a deleted page to a surviving page. */
export function imageReassignmentUpdatesForPageDelete(
    store: EntitySource,
    deletingPageId: string,
): EntityUpdateStates<ImageItem>[] {
    // Collect surviving pages sorted by creation time
    const survivingPages: Page[] = [];
    for (const p of store.find({ type: Page })) {
        if (p.id !== deletingPageId) survivingPages.push(p as Page);
    }
    if (survivingPages.length === 0) return [];

    survivingPages.sort((a, b) => {
        const cmp = a.created.localeCompare(b.created);
        return cmp !== 0 ? cmp : a.id.localeCompare(b.id);
    });
    const fallbackPageId = survivingPages[0].id;
    const survivingIds = new Set(survivingPages.map(p => p.id));

    // Find image items on the deleting page
    const imageItems: ImageItem[] = [];
    for (const item of store.find({ parentId: deletingPageId, type: ImageItem })) {
        imageItems.push(item as ImageItem);
    }

    const updates: EntityUpdateStates<ImageItem>[] = [];
    for (const img of imageItems) {
        const target = findImageReassignmentTarget(
            store, img, deletingPageId, survivingIds, fallbackPageId
        );
        if (!target || target === img.parentId) continue;

        const reassigned = img.copy();
        reassigned.replace({ parent_id: target } as any);
        updates.push({ original: img, updated: reassigned as ImageItem });
    }
    return updates;
}

/** Prefer a surviving page that already references this image in a CardNote. */
export function findImageReassignmentTarget(
    store: EntitySource,
    imageItem: ImageItem,
    deletingPageId: string,
    survivingIds: Set<string>,
    fallbackPageId: string,
): string | null {
    for (const entity of store.find({ type: CardNote })) {
        const note = entity as CardNote;
        if (note.parentId === deletingPageId) continue;
        if (!survivingIds.has(note.parentId)) continue;
        const imgRef = note.content.image;
        if (imgRef && imgRef.id === imageItem.id) {
            return note.parentId;
        }
    }
    return fallbackPageId;
}
