import { computed, makeObservable, observable, reaction } from "mobx";
import { Note, NoteData } from "../../model/Note";
import { calculateTextLayout } from "../../util";
import { pamet } from "../../facade";
import { Change } from "../../fusion/Change";
import { getLogger } from "../../fusion/logging";
import { DEFAULT_NOTE_FONT_FAMILY, DEFAULT_NOTE_FONT_FAMILY_GENERIC, DEFAULT_NOTE_FONT_SIZE, DEFAULT_NOTE_LINE_HEIGHT } from "../../constants";

let log = getLogger('NoteViewState.ts');

export const defaultFontString = `${DEFAULT_NOTE_FONT_SIZE}px/${DEFAULT_NOTE_LINE_HEIGHT}px ` +
    `'${DEFAULT_NOTE_FONT_FAMILY}', ` +
    `${DEFAULT_NOTE_FONT_FAMILY_GENERIC}`;

export interface TextLayoutData {
    lines: string[];
    is_elided: boolean;
    alignment: string;
}


export class NoteViewState {
    _noteData!: NoteData; // initialized in updateFromNote
    selected: boolean = false;

    constructor(note: Note) {
        this.updateFromNote(note);

        makeObservable(this, {
            _noteData: observable,
            note: computed,
            selected: observable,
            textLayoutData: computed
        });

        // Reimplement the above with a reaction
        reaction(() => pamet.noteStore.get(note.id), (note_: Note | undefined) => {
            if (note_ === undefined) {
                log.error('Could not update note component props, note not found, id:', note.id);
                return;
            }
            this.updateFromNote(note_);
            this.handleNoteUpdate(Change.update(note, note_)); // TMP
        });
    }
    get note(): Note {
        return new Note(this._noteData);
    }
    updateFromNote(note: Note) {
        this._noteData = note.data();
    }
    get textLayoutData(): TextLayoutData {
        return calculateTextLayout(this.note.content.text || '', this.note.textRect(), defaultFontString);
    }
    handleNoteUpdate = (change: Change) => {
        if (change.isUpdate()) {
            log.info('Note update', change);
        }
    }
}
