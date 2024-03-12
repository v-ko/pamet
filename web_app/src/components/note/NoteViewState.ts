import { computed, makeObservable, observable, reaction } from "mobx";
import { Note } from "../../model/Note";
import { TextLayoutData, calculateTextLayout } from "../../util";
import { pamet } from "../../facade";
import { Change } from "../../fusion/Change";
import { getLogger } from "../../fusion/logging";
import { PageChildViewState } from "../canvas/PageChildViewState";
import { defaultFontString, textRect } from "./NoteCanvasView";
import { SerializedEntity, dumpToDict, loadFromDict } from "../../fusion/libs/Entity";

let log = getLogger('NoteViewState.ts');


export class NoteViewState extends PageChildViewState {
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
    pageChild(): Note {
        return this.note;
    }
    updateFromNote(note: Note) {
        this._noteData = dumpToDict(note);
    }
    get textLayoutData(): TextLayoutData {
        return calculateTextLayout(this.note.content.text || '', textRect(this.note.rect()), defaultFontString);
    }
    handleNoteUpdate = (change: Change) => {
        if (change.isUpdate()) {
            log.info('Note update', change);
        }
    }

}
