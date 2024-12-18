import { action } from "fusion/libs/Action";
import { PageMode, PageViewState } from "../components/page/PageViewState";
import { NoteViewState } from "../components/note/NoteViewState";
import { Point2D } from "../util/Point2D";
import { Size } from "../util/Size";
import { snapVectorToGrid } from "../util";
import { pamet } from "../core/facade";
import { MAX_NOTE_HEIGHT, MAX_NOTE_WIDTH, MIN_NOTE_HEIGHT, MIN_NOTE_WIDTH } from "../core/constants";

class NoteActions {
    @action
    startNotesResize(state: PageViewState, mainNoteVS: NoteViewState, mousePosOnScreen: Point2D) {
        let mouseRealPos = state.viewport.unprojectPoint(mousePosOnScreen);
        let resizeNoteRect = mainNoteVS.note().rect();

        state.setMode(PageMode.NoteResize);
        state.noteResizeCircleClickOffset = mouseRealPos.subtract(
            resizeNoteRect.bottomRight());
        state.noteResizeClickRealPos = mouseRealPos;
        state.noteResizeInitialSize = resizeNoteRect.size();

        state.notesBeingResized = []
        for (let element of state.selectedElementsVS) {
            if (element instanceof NoteViewState) {
                state.notesBeingResized.push(element);
            }
        }
    }

    _newNoteSizeOnResize(state: PageViewState, mousePosOnScreen: Point2D): Size {
        let mouseRealPos = state.viewport.unprojectPoint(mousePosOnScreen);
        let resizeDelta = mouseRealPos.subtract(state.noteResizeClickRealPos);
        let newSize = state.noteResizeInitialSize.add(resizeDelta);
        newSize = snapVectorToGrid(newSize);
        newSize.x = Math.min(Math.max(newSize.x, MIN_NOTE_WIDTH), MAX_NOTE_WIDTH);
        newSize.y = Math.min(Math.max(newSize.y, MIN_NOTE_HEIGHT), MAX_NOTE_HEIGHT);

        return snapVectorToGrid(newSize);
    }

    @action
    notesResizeMove(state:PageViewState, mousePosOnScreen: Point2D) {
        let newSize = this._newNoteSizeOnResize(state, mousePosOnScreen);

        for (let noteVS of state.notesBeingResized) {
            let note = noteVS.note();
            let rect = note.rect();
            rect.setSize(snapVectorToGrid(newSize));
            note.setRect(rect);
            noteVS.updateFromNote(note);
        }
    }

    @action
    endNotesResize(state: PageViewState, mousePosOnScreen: Point2D) {
        let newSize: Size
        // If it's only a click - resize all selected to the size of the main note
        if (mousePosOnScreen.equals(state.noteResizeClickRealPos)) {
            newSize = state.noteResizeInitialSize;
        } else {
            newSize = this._newNoteSizeOnResize(state, mousePosOnScreen);
        }

        for (let noteVS of state.notesBeingResized) {
            let note = noteVS.note();
            let rect = note.rect();
            rect.setSize(newSize);
            note.setRect(rect);
            pamet.updateNote(note);
        }
        state.notesBeingResized = [];
        state.clearMode();
    }
}


export const noteActions = new NoteActions();
