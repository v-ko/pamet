import { computed, makeObservable, observable, reaction } from "mobx";
import { Note } from "../../model/Note";
import { TextLayout } from "../../util";
import { calculateTextLayout } from "./util";
import { pamet } from "../../facade";
import { Change } from "../../fusion/Change";
import { getLogger } from "../../fusion/logging";
import { ElementViewState } from "../page/ElementViewState";
import { DEFAULT_FONT_STRING } from "../../constants";
import { SerializedEntity, dumpToDict, loadFromDict } from "../../fusion/libs/Entity";

let log = getLogger('NoteViewState.ts');


export class NoteViewState extends ElementViewState {
    _noteData!: SerializedEntity; // initialized in updateFromNote

    constructor(note: Note) {
        super();
        this.updateFromNote(note);

        makeObservable(this, {
            _noteData: observable,
            note: computed,
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
        return loadFromDict(this._noteData) as Note
    }
    element(): Note {
        return this.note;
    }
    updateFromNote(note: Note) {
        this._noteData = dumpToDict(note);
    }
    get textLayoutData(): TextLayout {
        return calculateTextLayout(this.note.text, this.note.textRect(), DEFAULT_FONT_STRING);
    }
    handleNoteUpdate = (change: Change) => {
        if (change.isUpdate()) {
            log.info('Note update', change);
        }
    }

}
