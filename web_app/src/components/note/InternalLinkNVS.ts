import { computed, makeObservable, observable, reaction } from "mobx";
import { pamet } from "../../facade";
import { calculateTextLayout } from "../../util";
import { NoteViewState, defaultFontString } from "./NoteViewState";
import { PageData } from "../../model/Page";
import { Note } from "../../model/Note";

const MISSING_PAGE_TITLE = '(missing)'

export class InternalLinkNoteViewState extends NoteViewState {
    pageName: string = MISSING_PAGE_TITLE;

    constructor(note: Note){
        super(note)
        this._updatePageName()

        makeObservable(this, {
            // // Inherited // test without
            // _noteData: observable,
            // note: computed,
            // selected: observable,
            // textLayoutData: computed,
            // New
            pageName: observable,
        })

        reaction(() => pamet.page(this._pageId()), (page) => {
            this._updatePageName()
        })
    }

    _pageId(): string {
        let url = this.note.content.url
        if (url === undefined){
            throw Error('InternalLinkNote has no url')
        } else if (!url.startsWith('pamet:/p')){
            throw Error('InternalLinkNote has no url')
        }
        return url.split("/")[2]
    }

    _updatePageName(){
        let page = pamet.page(this._pageId())
        if (page === undefined){
            this.pageName = MISSING_PAGE_TITLE
            return
        }
        this.pageName = page.name
    }

    get textLayoutData(){
        return calculateTextLayout(this.pageName, this.note.textRect(), defaultFontString);
    }
}
