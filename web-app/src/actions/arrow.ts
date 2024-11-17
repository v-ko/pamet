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

        let anchorSuggestion = state.anchorSuggestionAt(realPos);
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
}

export const arrowActions = new ArrowActions();
