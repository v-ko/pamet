import { computed, makeObservable, observable, reaction } from "mobx";
import { Note } from "../../model/Note";
import { TextLayout } from "../../util";
import { calculateTextLayout } from "./util";
import { getLogger } from "pyfusion/logging";
import { ElementViewState } from "../page/ElementViewState";
import { DEFAULT_FONT_STRING } from "../../core/constants";
import { SerializedEntityData, dumpToDict, loadFromDict } from "pyfusion/libs/Entity";

let log = getLogger('NoteViewState.ts');


export class NoteViewState extends ElementViewState {
    _noteData!: SerializedEntityData; // initialized in updateFromNote

    constructor(note: Note) {
        super();
        this.updateFromNote(note);

        makeObservable(this, {
            _noteData: observable,
            _note: computed,
            textLayoutData: computed
        });
    }

    // Used to make use of mobx.computed, while making it visible that
    // the returned note is a new computed object, rather than a mutable property
    get _note(): Note {
        return loadFromDict(this._noteData) as Note
    }
    note(): Note {
        return this._note
    }
    element(): Note {
        return this.note();
    }
    updateFromNote(note: Note) {
        this._noteData = dumpToDict(note);
    }
    get textLayoutData(): TextLayout {
        let note = this.note();
        return calculateTextLayout(note.text, note.textRect(), DEFAULT_FONT_STRING);
    }
}
