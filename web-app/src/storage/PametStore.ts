
import { Change } from 'fusion/Change'
import { Store, SearchFilter } from 'fusion/storage/BaseStore'
import { IndexConfig, ENTITY_TYPE_INDEX_KEY } from 'fusion/storage/InMemoryStore'
import { Arrow } from '../model/Arrow'
import { Note } from '../model/Note'
import { Page } from '../model/Page'

// Pamet-specific index definitions including entity type indexing
export const PAMET_INMEMORY_STORE_CONFIG: readonly IndexConfig[] = [
    { name: "id", fields: [{ indexKey: "id" }], isUnique: true },
    {
        name: "type_id",
        fields: [
            { indexKey: ENTITY_TYPE_INDEX_KEY, allowedTypes: ['Page', 'Note', 'Arrow', 'MediaItem'] },
            { indexKey: 'id' }
        ],
        isUnique: true
    },
    {
        name: "parentId",
        fields: [{ indexKey: "parentId" }],
        isUnique: false
    },
    {
        name: "type_parentId",
        fields: [
            { indexKey: ENTITY_TYPE_INDEX_KEY, allowedTypes: ['Page', 'Note', 'Arrow', 'MediaItem'] },
            { indexKey: 'parentId' }
        ],
        isUnique: false
    },
    {
        name: "path",
        fields: [{ indexKey: 'path' }],
        isUnique: true
    }
];


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
