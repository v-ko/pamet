import type { Entity, EntityData } from 'fusion/model/Entity';
import { CardNote } from '@/model/CardNote';
import { Page } from '@/model/Page';

export const DELETED_LINK_TEXT_TEMPLATE = '(deleted %s)';

export function deletedLinkText(name: string): string {
    return DELETED_LINK_TEXT_TEMPLATE.replace('%s', name);
}

export function isDeletedLinkText(text: string): boolean {
    const prefix = DELETED_LINK_TEXT_TEMPLATE.split('%s')[0];
    const suffix = DELETED_LINK_TEXT_TEMPLATE.split('%s')[1];
    return text.startsWith(prefix) && text.endsWith(suffix);
}

/** Minimal interface for querying entities — satisfied by headStore, pamet facade, etc. */
export interface EntitySource {
    find(filter: any): Generator<any>;
    page?(pageId: string): Page | undefined;
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
    const deletedText = deletedLinkText(pageName);
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

/**
 * Check all notes with page_ref on a given page against the store.
 * Fix stale name/path if the target page exists, or mark as deleted if it doesn't.
 */
export function pageRefCorrectnessUpdates(
    store: EntitySource,
    pageId: string,
): EntityUpdateStates<CardNote>[] {
    if (!store.page) {
        throw new Error('pageRefCorrectnessUpdates requires a store with a page() method');
    }
    const updates: EntityUpdateStates<CardNote>[] = [];
    for (const note of store.find({ type: CardNote, parentId: pageId })) {
        const ref = (note as CardNote).content.page_ref;
        if (!ref) continue;

        const targetPage = store.page(ref.id);
        if (!targetPage) {
            // Target page was deleted — mark text if not already marked
            const currentText = (note as CardNote).content.text ?? '';
            if (isDeletedLinkText(currentText)) continue;

            const updated = (note as CardNote).copy();
            updated.replace({
                content: { ...updated.content, text: deletedLinkText(currentText) },
            } as any);
            updates.push({ original: note as CardNote, updated });
        } else {
            // Target page exists — fix stale name/path
            const expectedName = targetPage.name;
            const expectedPath = targetPage.path;
            const currentText = (note as CardNote).content.text ?? '';
            if (currentText === expectedName && ref.path === expectedPath) continue;

            const updated = (note as CardNote).copy();
            updated.replace({
                content: {
                    ...updated.content,
                    text: expectedName,
                    page_ref: { id: ref.id, path: expectedPath },
                },
            } as any);
            updates.push({ original: note as CardNote, updated });
        }
    }
    return updates;
}
