import { color_to_css_rgba_string } from "../../util";
import { Point2D } from "../../util/Point2D";
import { BaseCanvasView } from "../note/BaseCanvasView";
import { ArrowViewState } from "./ArrowViewState";

let ARROW_HAND_LENGTH = 20;
let ARROW_HAND_ANGLE =  25 ; // 25 degrees
let INCLINATION_MEASURE_AT = ARROW_HAND_LENGTH / 2; // units before the end

export class ArrowCanvasView extends BaseCanvasView {
    get arrowViewState(): ArrowViewState {
        return this.elementViewState as ArrowViewState;
    }
    render(context: CanvasRenderingContext2D) {
        let arrow = this.arrowViewState.arrow;

        // Draw the arrow line/path
        for (let curve of this.arrowViewState.bezierCurveParams) {
            context.beginPath();
            context.strokeStyle = color_to_css_rgba_string(arrow.color);
            context.lineWidth = arrow.line_thickness;
            context.moveTo(curve[0].x, curve[0].y);
            context.bezierCurveTo(curve[1].x, curve[1].y, curve[2].x, curve[2].y, curve[3].x, curve[3].y);
            context.stroke();
            context.closePath();
        }

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
        context.strokeStyle = color_to_css_rgba_string(arrow.color);
        context.lineWidth = arrow.line_thickness;
        context.moveTo(endPoint.x, endPoint.y);
        context.lineTo(handEnd.x, handEnd.y);
        context.moveTo(endPoint.x, endPoint.y);
        context.lineTo(handEnd2.x, handEnd2.y);
        context.stroke();
        context.closePath();
    }
}
