import { ARROW_SELECTION_THICKNESS_DELTA, SELECTED_ITEM_OVERLAY_COLOR_ROLE } from "@/core/constants";
import { color_role_to_hex_color } from "@/util";
import { BaseCanvasView } from "@/components/note/BaseCanvasView";
import { ArrowViewState } from "@/components/arrow/ArrowViewState";

const selectionColor = color_role_to_hex_color(SELECTED_ITEM_OVERLAY_COLOR_ROLE);

let ARROW_HAND_LENGTH = 20;
let ARROW_HAND_ANGLE =  25 ; // 25 degrees
let INCLINATION_MEASURE_AT = ARROW_HAND_LENGTH / 2; // units before the end

export class ArrowCanvasView extends BaseCanvasView {
    get arrowViewState(): ArrowViewState {
        return this.elementViewState as ArrowViewState;
    }

    _renderArrowHead(context: CanvasRenderingContext2D) {
        // Draw the arrow head - get the point at an ARROW_HAND_LENGTH from the
        // end of the path and get the inclination of the path using that
        // (which determines the direction of the arrow head)
        let arrowPath = this.arrowViewState.paperPath;
        let inclinationAt = arrowPath.length - INCLINATION_MEASURE_AT;
        let inclinationPoint = arrowPath.getPointAt(inclinationAt)
        let endPoint = arrowPath.lastSegment.point;
        let normalizedVec = endPoint.subtract(inclinationPoint).normalize();
        let arrowHandBase = endPoint.subtract(normalizedVec.multiply(ARROW_HAND_LENGTH));
        let handEnd = arrowHandBase.rotate(ARROW_HAND_ANGLE, endPoint);
        let handEnd2 = arrowHandBase.rotate(-ARROW_HAND_ANGLE, endPoint);
        context.beginPath();
        context.moveTo(endPoint.x, endPoint.y);
        context.lineTo(handEnd.x, handEnd.y);
        context.moveTo(endPoint.x, endPoint.y);
        context.lineTo(handEnd2.x, handEnd2.y);
        context.stroke();
        context.closePath();
    }

    _drawArrowBody(context: CanvasRenderingContext2D) {
        // Draw the arrow line/path
        for (let curve of this.arrowViewState.bezierCurveParams) {
            context.beginPath();
            context.moveTo(curve[0].x, curve[0].y);
            context.bezierCurveTo(curve[1].x, curve[1].y, curve[2].x, curve[2].y, curve[3].x, curve[3].y);
            context.stroke();
            context.closePath();
        }
    }

    render(context: CanvasRenderingContext2D) {
        let arrow = this.arrowViewState.arrow();

        context.strokeStyle = color_role_to_hex_color(arrow.colorRole);
        context.lineWidth = arrow.thickness;
        this._drawArrowBody(context);
        this._renderArrowHead(context);
    }

    renderSelectionOverlay(context: CanvasRenderingContext2D) {
        let arrow = this.arrowViewState.arrow();

        context.strokeStyle = selectionColor;
        context.lineWidth = arrow.thickness + ARROW_SELECTION_THICKNESS_DELTA;
        this._drawArrowBody(context);
        this._renderArrowHead(context);
    }
}
