
import { Change } from 'fusion/Change'
import { Store, SearchFilter } from 'fusion/storage/BaseStore'
import { IndexDefinition, EntityTypeIndexConfig } from 'fusion/storage/InMemoryStore'
import { Arrow } from '../model/Arrow'
import { Note } from '../model/Note'
import { Page } from '../model/Page'
import { MediaItem } from '../model/MediaItem'

// Entity type index configuration for Pamet domain objects
const PAMET_ENTITY_TYPE_CONFIG: EntityTypeIndexConfig = {
    indexKey: 'entityType',
    allowedTypes: [Page, Note, Arrow, MediaItem]
};

// Pamet-specific index definitions including entity type indexing
export const PAMET_INMEMORY_STORE_CONFIG: readonly IndexDefinition[] = [
    ["id"],                                    // Unique index for entity lookup by ID
    [PAMET_ENTITY_TYPE_CONFIG, "id"],         // Composite index for type-specific ID lookups
    ["parentId"],                             // Index for parent-child relationships
    [PAMET_ENTITY_TYPE_CONFIG, "parentId"],   // Composite index for type-specific parent lookups
    ["path"],                                 // Index for path-based lookups (e.g., media items)
] as const;


export abstract class PametStore extends Store {
    // Page CRUD
    insertPage(page: Page): Change {
        return this.insertOne(page)
    }
    updatePage(page: Page): Change {
        return this.updateOne(page)
    }
    removePageWithChildren(page: Page): Change[] {
        const changes: Change[] = [];

        // Find all entities with this page as parent
        const children = Array.from(this.find({ parentId: page.id }));

        // Remove all children
        for (const child of children) {
            changes.push(this.removeOne(child));
        }

        // Remove the page itself
        changes.push(this.removeOne(page));

        return changes;
    }

    removePage(page: Page): Change {
        return this.removeOne(page)
    }
    pages(filter: SearchFilter = {}): Generator<Page>{
        filter.type = Page
        return this.find(filter) as Generator<Page>
    }
    page(page_id: string): Page | undefined {
        return this.findOne({id: page_id}) as Page | undefined
    }

    // Note CRUD
    insertNote(note: Note): Change {
        return this.insertOne(note)
    }
    updateNote(note: Note): Change {
        return this.updateOne(note)
    }
    removeNote(note: Note): Change {
        return this.removeOne(note)
    }
    notes(filter: SearchFilter = {}): Generator<Note>{
        filter.type = Note
        return this.find(filter) as Generator<Note>
    }
    note(note_id: string): Note | undefined {
        return this.findOne({id: note_id}) as Note | undefined
    }

    //Arrow CRUD
    insertArrow(arrow: Arrow): Change {
        return this.insertOne(arrow)
    }
    updateArrow(arrow: Arrow): Change {
        return this.updateOne(arrow)
    }
    removeArrow(arrow: Arrow): Change {
        return this.removeOne(arrow)
    }
    arrows(filter: SearchFilter = {}): Generator<Arrow>{
        filter.type = Arrow
        return this.find(filter) as Generator<Arrow>
    }
    arrow(arrow_id: string): Arrow | undefined {
        return this.findOne({id: arrow_id}) as Arrow | undefined
    }
}
