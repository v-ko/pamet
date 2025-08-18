import { computed, makeObservable, observable, toJS } from "mobx";
import { Note, SerializedNote } from "@/model/Note";
import { TextLayout } from "@/util";
import { calculateTextLayout } from "@/components/note/note-dependent-utils";
import { getLogger } from "fusion/logging";
import { ElementViewState } from "@/components/page/ElementViewState";
import { DEFAULT_FONT_STRING } from "@/core/constants";
import { loadFromDict } from "fusion/model/Entity";
import { Change } from "fusion/model/Change";
import { PageViewState } from "@/components/page/PageViewState";

let log = getLogger('NoteViewState.ts');


export class NoteViewState extends ElementViewState {
    _elementData!: SerializedNote; // initialized in the element constructor

    constructor(note: Note, pageViewState: PageViewState) {
        super(note, pageViewState);

        makeObservable(this, {
            _elementData: observable,
            // _note: computed,  This returns instances with the same data object (and entities arer expected to be generally immutable )
            textLayoutData: computed
        });

    }

    // Used to make use of mobx.computed, while making it visible that
    // the returned note is a new computed object, rather than a mutable property
    get _note(): Note {
        // We need to copy the _data, since it's wrapped in a mobx.observable
        // and we want to drop the wrapper
        // https://mobx.js.org/observable-state.html#converting-observables-back-to-vanilla-javascript-collections
        let noteData = toJS(this._elementData);
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
        this._elementData = { ...this._elementData, ...update };
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
