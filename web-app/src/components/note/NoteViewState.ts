import { computed, makeObservable, observable } from "mobx";
import { Note } from "../../model/Note";
import { TextLayout } from "../../util";
import { calculateTextLayout } from "./util";
import { getLogger } from "fusion/logging";
import { ElementViewState } from "../page/ElementViewState";
import { DEFAULT_FONT_STRING } from "../../core/constants";
import { SerializedEntityData, dumpToDict, loadFromDict } from "fusion/libs/Entity";
import { pamet } from '../../core/facade';

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
        // We need to copy the _data, since it's wrapped in a mobx.observable
        // and we want to drop the wrapper
        // https://mobx.js.org/observable-state.html#converting-observables-back-to-vanilla-javascript-collections
        // let noteData = {...this._noteData};
        // return loadFromDict(noteData) as Note
        // return loadFromDict(this._noteData) as Note
        // Or just use the pamet object
        let note = pamet.findOne({id: this._noteData.id});
        if (note === null) {
            throw new Error(`Note with id ${this._noteData.id} not found`);
        }
        return note as Note;
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
