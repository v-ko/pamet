
import { Change } from '../fusion/Change'
import { Repository, SearchFilter } from '../fusion/storage/BaseRepository'
import { Arrow } from '../model/Arrow'
import { Note } from '../model/Note'
import { Page } from '../model/Page'

export abstract class PametRepository extends Repository {
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
        return this.find(filter)
    }
    page(page_id: string): Page | undefined {
        return this.findOne({id: page_id})
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
        return this.find(filter)
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
        return this.find(filter)
    }
}
