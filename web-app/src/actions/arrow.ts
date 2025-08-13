import { action } from "fusion/registries/Action";
import { PageMode, PageViewState } from "@/components/page/PageViewState";
import { ArrowViewState } from "@/components/arrow/ArrowViewState";
import { Arrow, ArrowAnchorOnNoteType, ArrowAnchorTypeToString } from "@/model/Arrow";
import { Point2D, PointData } from "fusion/primitives/Point2D";
import { NoteViewState } from "@/components/note/NoteViewState";
import { DEFAULT_ARROW_THICKNESS } from "@/core/constants";
import { pamet } from "@/core/facade";
import { elementId } from "@/model/Element";
import { getEntityId } from "fusion/model/Entity";
import { getLogger } from "fusion/logging";
import { snapVectorToGrid } from "@/util";
import { Note } from "@/model/Note";

let log = getLogger('ArrowActions.ts');

class ArrowActions {
    @action
    startArrowCreation(state: PageViewState) {
        state.mode = PageMode.CreateArrow
    }

    @action
    arrowCreationClick(state: PageViewState, position: Point2D) {
        console.log("Arrow creation click");
        // Check if the click was on the canvas or on an object of interest
        // (note or note arrow anchor)
        let realPos = state.viewport.unprojectPoint(position);
        let noteVS_underMouse: NoteViewState | null = null;
        let anchorUnderMouse: ArrowAnchorOnNoteType = ArrowAnchorOnNoteType.none;
        let anchorPos = realPos; // Default to the mouse position

        let anchorSuggestion = state.noteAnchorSuggestionAt(realPos);
        if (anchorSuggestion.onAnchor || anchorSuggestion.onNote) {
            noteVS_underMouse = anchorSuggestion.noteViewState;
            anchorUnderMouse = anchorSuggestion.anchorType;
            anchorPos = anchorSuggestion.position;
        }

        // If it's the first click - add the view state and set the tail pos
        // createArrow mode + newArrowViewState=null imples the first click
        if (state.newArrowViewState === null) {
            let tail_coords: PointData | null;
            let tail_note_id: string | null;
            let colorRole = 'onPrimary';
            if (noteVS_underMouse) {
                let note = noteVS_underMouse.note();
                tail_coords = null;
                tail_note_id = note.own_id;
                colorRole = note.style.color_role;
            } else {
                tail_coords = anchorPos.data();
                tail_note_id = null;
            }

            let arrow = new Arrow({
                id: elementId(state.page.id, getEntityId()),
                tail: {
                    position: tail_coords,
                    noteAnchorId: tail_note_id,
                    noteAnchorType: ArrowAnchorTypeToString[anchorUnderMouse],
                },
                head: {
                    position: null,
                    noteAnchorId: null,
                    noteAnchorType: ArrowAnchorTypeToString[ArrowAnchorOnNoteType.none],
                },
                mid_points: [],
                style: {
                    color_role: colorRole,
                    line_type: "solid",
                    thickness: DEFAULT_ARROW_THICKNESS,
                    line_function: "bezier_cubic",
                    head_shape: "arrow",
                    tail_shape: "arrow",
                }
            });
            state.newArrowViewState = new ArrowViewState(arrow);

        } else { // Second click - finish note creation
            // createArrow mode and newArrowViewState present implies second click
            let arrow = state.newArrowViewState.arrow();
            if (noteVS_underMouse) {
                arrow.setHead(null, noteVS_underMouse.note(), anchorUnderMouse);
            } else {
                arrow.setHead(realPos, null, ArrowAnchorOnNoteType.none);
            }

            let invalidArrow = false;
            // If both ends of the arrow are at the same point - cancel it
            if (arrow.headPoint && arrow.tailPoint) {
                if (arrow.headPoint!.equals(arrow.tailPoint!)) {
                    log.info('Arrow head and tail coords are the same');
                    invalidArrow = true;
                }
            }

            //Similarly check if both ends are on the same anchor of the same note
            if (arrow.headAnchoredOnNote && arrow.tailAnchoredOnNote) {
                if (arrow.headNoteId === arrow.tailNoteId && arrow.headAnchorType === arrow.tailAnchorType) {
                    log.info('Arrow head and tail anchors are the same');
                    invalidArrow = true;
                }
            }

            // Since the arrow is complete, we can add it to the page
            if (!invalidArrow) {

                pamet.insertArrow(arrow);
            }
            state.clearMode();
        }
    }

    @action
    startControlPointDrag(state: PageViewState, controlPointIndex: number) {
        state.mode = PageMode.ArrowControlPointDrag;
        state.draggedControlPointIndex = controlPointIndex;
    }

    @action
    controlPointDragMove(state: PageViewState, mousePos: Point2D) {
        let arrowVS = state.arrowVS_withVisibleControlPoints();

        if (arrowVS === null) {
            throw Error('No arrow with visible control points found');
        }
        if (state.draggedControlPointIndex === null) {
            throw Error('No control point being dragged');
        }

        // Get suggested anchor at mouse pos
        let realMousePos = state.viewport.unprojectPoint(mousePos)
        let anchorSuggestion = state.noteAnchorSuggestionAt(realMousePos)

        let controlPoint: Point2D | null = null;
        let suggestionNote: Note | null = null;
        let suggestionAnchorType: ArrowAnchorOnNoteType = ArrowAnchorOnNoteType.none;
        let mouseSnapped = snapVectorToGrid(realMousePos);

        // If on an anchor
        if (anchorSuggestion.onAnchor) {
            suggestionNote = anchorSuggestion.noteViewState.note();
            suggestionAnchorType = anchorSuggestion.anchorType;
        } else if (anchorSuggestion.onNote) {
            // If no anchor, but still on the note body
            suggestionNote = anchorSuggestion.noteViewState.note();
            suggestionAnchorType = ArrowAnchorOnNoteType.auto;
        } else {
            // Else on empty space - snap to grid
            controlPoint = mouseSnapped;
        }

        // Update the control point
        let arrow = arrowVS.arrow();
        let controlPointIndices = arrow.controlPointIndices();
        let headIndex = controlPointIndices[controlPointIndices.length - 1];

        // If the CP is the head or tail - set it via the respective setter
        // (only here can we have note anchors)
        if (state.draggedControlPointIndex === 0) {
            arrow.setTail(controlPoint, suggestionNote, suggestionAnchorType);
            arrowVS.updateFromArrow(arrow);
        } else if (state.draggedControlPointIndex === headIndex) {
            arrow.setHead(controlPoint, suggestionNote, suggestionAnchorType);
            arrowVS.updateFromArrow(arrow);

        } else if (controlPointIndices.includes(state.draggedControlPointIndex)) {
            // It's a mid point
            let midPointIndex = state.draggedControlPointIndex - 1;
            let midPoints = arrow.midPoints;
            midPoints[midPointIndex] = mouseSnapped;
            arrow.replaceMidpoints(midPoints);
            arrowVS.updateFromArrow(arrow);
        } else {
            throw Error('Clicks on suggested control point indices should be handled in createControlPoint');
        }
    }

    @action
    endControlPointDrag(state: PageViewState, mousePos: Point2D) {
        let arrowVS = state.arrowVS_withVisibleControlPoints();

        if (arrowVS === null) {
            throw Error('No arrow with visible control points found');
        }
        if (state.draggedControlPointIndex === null) {
            throw Error('No control point being dragged');
        }
        if ((state.draggedControlPointIndex % 1) !== 0) {
            // If it's a suggested midpoint - do nothing
            state.clearMode();
            return;
        }

        // Get suggested anchor at mouse pos
        let realMousePos = state.viewport.unprojectPoint(mousePos)
        let anchorSuggestion = state.noteAnchorSuggestionAt(realMousePos)

        let controlPoint: Point2D | null = null;
        let suggestionNote: Note | null = null;
        let suggestionAnchorType: ArrowAnchorOnNoteType = ArrowAnchorOnNoteType.none;
        let mouseSnapped = snapVectorToGrid(realMousePos);

        // If on an anchor
        if (anchorSuggestion.onAnchor) {
            suggestionNote = anchorSuggestion.noteViewState.note();
            suggestionAnchorType = anchorSuggestion.anchorType;
        } else if (anchorSuggestion.onNote) {
            // If no anchor, but still on the note body
            suggestionNote = anchorSuggestion.noteViewState.note();
            suggestionAnchorType = ArrowAnchorOnNoteType.auto;
        } else {
            // Else on empty space - snap to grid
            controlPoint = mouseSnapped;
        }

        // Update the control point
        let arrow = arrowVS.arrow();
        let controlPointIndices = arrow.controlPointIndices();
        let headIndex = controlPointIndices[controlPointIndices.length - 1];

        if (state.draggedControlPointIndex === 0) {
            arrow.setTail(controlPoint, suggestionNote, suggestionAnchorType);
        } else if (state.draggedControlPointIndex === headIndex) {
            arrow.setHead(controlPoint, suggestionNote, suggestionAnchorType);

        } else if (controlPointIndices.includes(state.draggedControlPointIndex)) {
            // It's a mid point
            let midPointIndex = state.draggedControlPointIndex - 1;
            let midPoints = arrow.midPoints;
            midPoints[midPointIndex] = mouseSnapped;
            arrow.replaceMidpoints(midPoints);
        }

        // Update the entity
        pamet.updateArrow(arrow);
        state.clearMode();
    }

    @action
    createControlPointAndStartDrag(state: PageViewState, realPosition: Point2D, suggestedIndex: number) {
        let arrowVS = state.arrowVS_withVisibleControlPoints();
        if (arrowVS === null) {
            throw Error('No arrow with visible control points found');
        }

        let arrow = arrowVS.arrow();
        let mouseSnapped = snapVectorToGrid(realPosition);
        let potentialCP_indices = arrow.potentialControlPointIndices();

        // It's a suggested midpoint (with a .5 index)
        let midPointIndex = potentialCP_indices.indexOf(suggestedIndex);
        if (midPointIndex === -1) {
            throw Error('Clicks on suggested control point indices should be handled in controlPointDragMove');
        }
        let midPoints = arrow.midPoints;
        midPoints.splice(midPointIndex, 0, mouseSnapped);
        let newMidPointIndex = midPointIndex + 1;
        arrow.replaceMidpoints(midPoints);

        // Update the entity (we've created a new control point)
        pamet.updateArrow(arrow);

        this.startControlPointDrag(state, newMidPointIndex);
    }

    @action
    deleteControlPoint(state: ArrowViewState, cpIndex: number) {
        let arrow = state.arrow();
        let midPoints = arrow.midPoints;
        midPoints.splice(cpIndex - 1, 1); // tail is 0, then midpoints, then head is last
        arrow.replaceMidpoints(midPoints);
        pamet.updateArrow(arrow);
    }
}

export const arrowActions = new ArrowActions();
