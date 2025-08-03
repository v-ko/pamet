import { computed, makeObservable, observable, reaction, toJS } from "mobx";
import { Note, SerializedNote } from "../../model/Note";
import { TextLayout } from "../../util";
import { calculateTextLayout } from "./note-dependent-utils";
import { getLogger } from "fusion/logging";
import { ElementViewState } from "../page/ElementViewState";
import { DEFAULT_FONT_STRING } from "../../core/constants";
import { dumpToDict, loadFromDict } from "fusion/libs/Entity";
import { pamet } from '../../core/facade';
import { Change } from "fusion/Change";

let log = getLogger('NoteViewState.ts');


export class NoteViewState extends ElementViewState {
    _noteData!: SerializedNote; // initialized in updateFromNote

    constructor(note: Note) {
        super();
        this._noteData = dumpToDict(note) as SerializedNote;

        makeObservable(this, {
            _noteData: observable,
            // _note: computed,  This returns instances with the same data object (and entities arer expected to be generally immutable )
            textLayoutData: computed
        });

        reaction(() => {
            return {content: this._noteData.content, style: this._noteData.style}
        }, () => {
            pamet.appViewState.currentPageViewState?._renderer.deleteNvsCache(this);
        });
    }

    // Used to make use of mobx.computed, while making it visible that
    // the returned note is a new computed object, rather than a mutable property
    get _note(): Note {
        // We need to copy the _data, since it's wrapped in a mobx.observable
        // and we want to drop the wrapper
        // https://mobx.js.org/observable-state.html#converting-observables-back-to-vanilla-javascript-collections
        let noteData = toJS(this._noteData);
        return loadFromDict(noteData) as Note
        // return loadFromDict(this._noteData) as Note << this won't work
        // Using the pamet.find method will cause problems with outdated state
    }
    note(): Note {
        return this._note
    }
    element(): Note {
        return this.note();
    }
    updateFromChange(change: Change) {
        if (!change.isUpdate) {
            log.error('Can only update from an update type change');
            return;
        }
        let update = change.forwardComponent as Partial<SerializedNote>;
        this._noteData = { ...this._noteData, ...update };
    }

    updateFromNote(note: Note) {
        // Needed since the note type can be changed at runtime from the user
        let change = this.note().changeFrom(note)
        this.updateFromChange(change);
    }
    get textLayoutData(): TextLayout {
        let note = this.note();
        return calculateTextLayout(note.text, note.textRect(), DEFAULT_FONT_STRING);
    }
}
