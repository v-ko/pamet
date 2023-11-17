import { computed, makeObservable, observable } from "mobx";
import { Note, NoteData } from "../../model/Note";
import { calculateTextLayout } from "../../util";
import { pamet } from "../../facade";
import { Change } from "../../fusion/Change";
import { getLogger } from "../../fusion/logging";
import { DEFAULT_NOTE_FONT_FAMILY, DEFAULT_NOTE_FONT_FAMILY_GENERIC, DEFAULT_NOTE_FONT_SIZE, DEFAULT_NOTE_LINE_HEIGHT } from "../../constants";

let log = getLogger('NoteViewState.ts');


export interface TextLayoutData {
    lines: string[];
    is_elided: boolean;
    alignment: string;
}


export class NoteViewState extends Note {
    selected: boolean = false;

    constructor(note: Note) {
        super(note._data);

        makeObservable(this, {
            _data: observable,
            content: computed,
            geometry: computed,
            style: computed,
            created: computed,
            modified: computed,
            tags: computed,
            selected: observable,
            textLayoutData: computed
        });

        // Register to note updates
        pamet.rawChagesByIdChannel.subscribe(this.handleNoteUpdate, note.id);
    }
    updateFromNote(note: Note) {
        Object.keys(note._data).forEach((key) => {
            this._data[key] = note._data[key];
        });
    }
    get textLayoutData(): TextLayoutData {
        // TMP?
        const fontString = `${DEFAULT_NOTE_FONT_SIZE}px/${DEFAULT_NOTE_LINE_HEIGHT}px ` +
            `'${DEFAULT_NOTE_FONT_FAMILY}', ` +
            `${DEFAULT_NOTE_FONT_FAMILY_GENERIC}`;

        return calculateTextLayout(this.content.text || '', this.textRect(), fontString);
    }
    handleNoteUpdate = (change: Change) => {
        if (change.isUpdate()) {
            log.info('Note update', change);
        }
    }
}
