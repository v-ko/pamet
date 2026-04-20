import type { Entity, EntityData } from 'fusion/model/Entity';
import { CardNote } from '@/model/CardNote';
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
