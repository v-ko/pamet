import { action } from "fusion/libs/Action";
import { PageMode, PageViewState } from "../components/page/PageViewState";
import { ArrowViewState } from "../components/arrow/ArrowViewState";
import { Arrow, ArrowAnchorType } from "../model/Arrow";
import { Point2D, PointData } from "../util/Point2D";
import { NoteViewState } from "../components/note/NoteViewState";
import { DEFAULT_ARROW_THICKNESS } from "../core/constants";
import { pamet } from "../core/facade";
import { elementId } from "../model/Element";
import { getEntityId } from "fusion/libs/Entity";
import { getLogger } from "fusion/logging";
import { snapVectorToGrid } from "../util";
import { Note } from "../model/Note";

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
        let anchorUnderMouse: ArrowAnchorType = ArrowAnchorType.none;
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
                tail_coords: tail_coords,
                head_coords: null,  // Follow mouse when head is not set
                mid_point_coords: [],
                tail_note_id: tail_note_id,
                head_note_id: null,
                tail_anchor: anchorUnderMouse,
                head_anchor: ArrowAnchorType.none,
                color_role: colorRole,
                line_type: "solid",
                line_thickness: DEFAULT_ARROW_THICKNESS,
                line_function_name: "bezier_cubic",
                head_shape: "arrow",
                tail_shape: "arrow",
            });
            state.newArrowViewState = new ArrowViewState(arrow, null, noteVS_underMouse);

        } else { // Second click - finish note creation
            // createArrow mode and newArrowViewState present implies second click
            let arrow = state.newArrowViewState.arrow();
            if (noteVS_underMouse) {
                arrow.setHead(null, noteVS_underMouse.note(), anchorUnderMouse);
            } else {
                arrow.setHead(realPos, null, ArrowAnchorType.none);
            }

            let invalidArrow = false;
            // If both ends of the arrow are at the same point - cancel it
            if (arrow.head_coords && arrow.tail_coords) {
                if (arrow.headPoint!.equals(arrow.tailPoint!)) {
                    log.info('Arrow head and tail coords are the same');
                    invalidArrow = true;
                }
            }

            //Similarly check if both ends are on the same anchor of the same note
            if (arrow.hasHeadAnchor() && arrow.hasTailAnchor()) {
                if (arrow.head_note_id === arrow.tail_note_id && arrow.head_anchor === arrow.tail_anchor) {
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
    startArrowEdgeDrag(state: PageViewState, edgeIndex: number) {
        state.mode = PageMode.ArrowEdgeDrag;
        state.draggedEdgeIndex = edgeIndex;
    }

    @action
    arrowEdgeDrag(state: PageViewState, mousePos: Point2D) {
        let arrowVS = state.arrowVS_withVisibleControlPoints();

        if (arrowVS === null) {
            throw Error('No arrow with visible control points found');
        }
        if (state.draggedEdgeIndex === null) {
            throw Error('No edge being dragged');
        }

        // Get suggested anchor at mouse pos
        let realMousePos = state.viewport.unprojectPoint(mousePos)
        let anchorSuggestion = state.noteAnchorSuggestionAt(realMousePos)

        let edge_coord: Point2D | null = null;
        let edge_note: Note | null = null;
        let edge_anchor: ArrowAnchorType = ArrowAnchorType.none;
        let mouseSnapped = snapVectorToGrid(realMousePos);

        // If on an anchor
        if (anchorSuggestion.onAnchor) {
            edge_note = anchorSuggestion.noteViewState.note();
            edge_anchor = anchorSuggestion.anchorType;
        } else if (anchorSuggestion.onNote) {
            // If no anchor, but still on the note body
            edge_note = anchorSuggestion.noteViewState.note();
            edge_anchor = ArrowAnchorType.auto;
        } else {
            // Else on empty space - snap to grid
            edge_coord = mouseSnapped;
        }

        // Update the edge
        let arrow = arrowVS.arrow();
        let edgeIndices = arrow.edgeIndices();
        let potentialEdgeIndices = arrow.potentialEdgeIndices();
        let headIndex = edgeIndices[edgeIndices.length - 1];

        // If the edge is the head or tail - set it via the respective setter
        // (only here can we have note anchors)
        if (state.draggedEdgeIndex === 0) {
            arrow.setTail(edge_coord, edge_note, edge_anchor);
            let { headNVS, tailNVS } = state.noteVS_anchorsForArrow(arrow);
            arrowVS.updateFromArrow(arrow, headNVS, tailNVS);
        } else if (state.draggedEdgeIndex === headIndex) {
            arrow.setHead(edge_coord, edge_note, edge_anchor);
            let { headNVS, tailNVS } = state.noteVS_anchorsForArrow(arrow);
            arrowVS.updateFromArrow(arrow, headNVS, tailNVS);

        } else if (edgeIndices.includes(state.draggedEdgeIndex)) {
            // It's a mid point
            let midPointIndex = state.draggedEdgeIndex - 1;
            let midPoints = arrow.mid_points;
            midPoints[midPointIndex] = mouseSnapped;
            arrow.replaceMidpoints(midPoints);
            arrowVS.updateFromArrow(arrow, arrowVS.headAnchorNoteViewState, arrowVS.tailAnchorNoteViewState);
        } else {
            throw Error('Clicks on suggested edge indices should be handled in createControlPoint');
        }
    }

    @action
    endArrowEdgeDrag(state: PageViewState, mousePos: Point2D) {
        let arrowVS = state.arrowVS_withVisibleControlPoints();

        if (arrowVS === null) {
            throw Error('No arrow with visible control points found');
        }
        if (state.draggedEdgeIndex === null) {
            throw Error('No edge being dragged');
        }
        if ((state.draggedEdgeIndex % 1) !== 0) {
            // If it's a suggested midpoint - do nothing
            state.clearMode();
            return;
        }

        // Get suggested anchor at mouse pos
        let realMousePos = state.viewport.unprojectPoint(mousePos)
        let anchorSuggestion = state.noteAnchorSuggestionAt(realMousePos)

        let edge_coord: Point2D | null = null;
        let edge_note: Note | null = null;
        let edge_anchor: ArrowAnchorType = ArrowAnchorType.none;
        let mouseSnapped = snapVectorToGrid(realMousePos);

        // If on an anchor
        if (anchorSuggestion.onAnchor) {
            edge_note = anchorSuggestion.noteViewState.note();
            edge_anchor = anchorSuggestion.anchorType;
        } else if (anchorSuggestion.onNote) {
            // If no anchor, but still on the note body
            edge_note = anchorSuggestion.noteViewState.note();
            edge_anchor = ArrowAnchorType.auto;
        } else {
            // Else on empty space - snap to grid
            edge_coord = mouseSnapped;
        }

        // Update the edge
        let arrow = arrowVS.arrow();
        let edgeIndices = arrow.edgeIndices();
        let headIndex = edgeIndices[edgeIndices.length - 1];

        if (state.draggedEdgeIndex === 0) {
            arrow.setTail(edge_coord, edge_note, edge_anchor);
        } else if (state.draggedEdgeIndex === headIndex) {
            arrow.setHead(edge_coord, edge_note, edge_anchor);

        } else if (edgeIndices.includes(state.draggedEdgeIndex)) {
            // It's a mid point
            let midPointIndex = state.draggedEdgeIndex - 1;
            let midPoints = arrow.mid_points;
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
        let potentialEdgeIndices = arrow.potentialEdgeIndices();

        // It's a suggested midpoint (with a .5 index)
        let midPointIndex = potentialEdgeIndices.indexOf(suggestedIndex);
        if (midPointIndex === -1) {
            throw Error('Clicks on suggested edge indices should be handled in arrowEdgeDrag');
        }
        let midPoints = arrow.mid_points;
        midPoints.splice(midPointIndex, 0, mouseSnapped);
        let newMidPointIndex = midPointIndex + 1;
        arrow.replaceMidpoints(midPoints);

        // Update the entity (we've created a new control point)
        pamet.updateArrow(arrow);

        this.startArrowEdgeDrag(state, newMidPointIndex);
    }

    @action
    deleteControlPoint(state: ArrowViewState, cpIndex: number) {
        let arrow = state.arrow();
        let midPoints = arrow.mid_points;
        midPoints.splice(cpIndex - 1, 1); // tail is 0, then midpoints, then head is last
        arrow.replaceMidpoints(midPoints);
        pamet.updateArrow(arrow);
    }
}

export const arrowActions = new ArrowActions();
