
import { Change } from 'pyfusion/Change'
import { Store, SearchFilter } from 'pyfusion/storage/BaseStore'
import { Arrow } from '../model/Arrow'
import { Note } from '../model/Note'
import { Page } from '../model/Page'

export interface SerializedPametDomainStoreState {
    pages: Page[];
    notes: Note[];
    arrows: Arrow[];
}

export abstract class PametStore extends Store {
    // Page CRUD
    insertPage(page: Page): Change {
        return this.insertOne(page)
    }
    updatePage(page: Page): Change {
        return this.updateOne(page)
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
}
