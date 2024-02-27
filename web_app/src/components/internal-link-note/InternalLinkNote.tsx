import { reaction } from "mobx";
import { Note } from "../../model/Note";
import { NoteViewState } from "../note/NoteViewState";
import { pamet } from "../../facade";
import { Page } from "../../model/Page";


const PAGE_NOT_FOUND = 'Page not found';


class InternalLinkNoteViewState extends NoteViewState {
    pageTitle: string = PAGE_NOT_FOUND;

    constructor(note: Note) {
        super(note);

        // Set page title initially
        const page = pamet.page(note.page_id);
        this._handlePageChange(page);

        // react to page change
        reaction(() => pamet.page(note.page_id), (page) => {
            this._handlePageChange(page);
        });
    }

    _handlePageChange(page: Page | undefined) {
        if (page === undefined) {
            this._noteData.content.text = PAGE_NOT_FOUND;
            return;
        }
        this._noteData.content.text = page.name;
    }
}
