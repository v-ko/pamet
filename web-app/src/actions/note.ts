import { action } from "fusion/libs/Action";
import { PageMode, PageViewState } from "../components/page/PageViewState";
import { NoteViewState } from "../components/note/NoteViewState";
import { Point2D } from "../util/Point2D";
import { Size } from "../util/Size";
import { snapVectorToGrid } from "../util";
import { pamet } from "../core/facade";
import { MAX_NOTE_HEIGHT, MAX_NOTE_WIDTH, MIN_NOTE_HEIGHT, MIN_NOTE_WIDTH } from "../core/constants";
import { ArrowViewState } from "../components/arrow/ArrowViewState";

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
    notesResizeMove(state: PageViewState, mousePosOnScreen: Point2D) {
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
    @action
    startMovingElements(state: PageViewState, mousePosOnScreen: Point2D) {
        state.mode = PageMode.MoveElements;
        state.realMousePosOnElementMoveStart = state.viewport.unprojectPoint(mousePosOnScreen);

        state.movedNoteVSs = [];
        state.movedArrowVSs = [];
        for (let element of state.selectedElementsVS) {
            if (element instanceof NoteViewState) {
                state.movedNoteVSs.push(element);
            } else if (element instanceof ArrowViewState) {
                state.movedArrowVSs.push(element);
            }
        }
    }
    _elementsMoveUpdate(state: PageViewState, mousePosOnScreen: Point2D, final: boolean) {
        let realMousePos = state.viewport.unprojectPoint(mousePosOnScreen)
        let realDelta = realMousePos.subtract(state.realMousePosOnElementMoveStart)

        let movedNoteIds = [];
        for (let noteVS of state.movedNoteVSs) {
            let viewStateNote = noteVS.note();
            let initialNote = pamet.note(viewStateNote.id);
            if (!initialNote) {
                throw new Error('Entity for moved note not found');
            }

            movedNoteIds.push(initialNote.own_id);

            let rect = initialNote.rect();
            rect.setTopLeft(snapVectorToGrid(rect.topLeft().add(realDelta)));
            if (final) {
                initialNote.setRect(rect);
                pamet.updateNote(initialNote);
            } else {
                viewStateNote.setRect(rect);
                let noteVS = state.viewStateForElement(viewStateNote.own_id) as NoteViewState;
                noteVS.updateFromNote(viewStateNote);
            }
        }

        for (let arrowVS of state.movedArrowVSs) {
            let initialArrow = pamet.arrow(arrowVS.arrow().id);
            if (!initialArrow) {
                throw new Error('Entity for moved arrow not found');
            }
            let viewStateArrow = arrowVS.arrow();
            let tailMoved: boolean;
            let headMoved: boolean;
            if (viewStateArrow.tailPoint) {
                viewStateArrow.tailPoint = snapVectorToGrid(
                    initialArrow.tailPoint!.add(realDelta));
                tailMoved = true;
            } else {
                tailMoved = movedNoteIds.includes(initialArrow.tailNoteId!);
            }
            if (viewStateArrow.headPoint) {
                viewStateArrow.headPoint = snapVectorToGrid(
                    initialArrow.headPoint!.add(realDelta));
                headMoved = true;
            } else {
                headMoved = movedNoteIds.includes(initialArrow.headNoteId!);
            }

            // If both head and tail are anchored to notes which move - move midpoints
            if (tailMoved && headMoved) {
                let midPoints = initialArrow.midPoints.map(
                    (p) => snapVectorToGrid(p.add(realDelta)));
                viewStateArrow.replaceMidpoints(midPoints);
            }

            if (final) {
                initialArrow.tailPoint = viewStateArrow.tailPoint;
                initialArrow.headPoint = viewStateArrow.headPoint;
                initialArrow.replaceMidpoints(viewStateArrow.midPoints);
                pamet.updateArrow(initialArrow);
            } else {
                let { headNVS, tailNVS } = state.noteVS_anchorsForArrow(viewStateArrow);
                let arrowVS = state.viewStateForElement(viewStateArrow.own_id) as ArrowViewState;
                arrowVS.updateFromArrow(viewStateArrow, headNVS, tailNVS);
            }
        }
    }
    @action
    elementsMoveUpdate(state: PageViewState, mousePosOnScreen: Point2D) {
        this._elementsMoveUpdate(state, mousePosOnScreen, false);
    }
    @action
    endElementsMove(state: PageViewState, mousePosOnScreen: Point2D) {
        this._elementsMoveUpdate(state, mousePosOnScreen, true);
        state.movedNoteVSs = [];  // If left full - it would be accepted as
        state.movedArrowVSs = []; // if the move was aboerted in the clearMode
        state.clearMode();
    }

}


export const noteActions = new NoteActions();
