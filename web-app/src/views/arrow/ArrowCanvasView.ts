import { ARROW_HAND_ANGLE_RAD, ARROW_HAND_LENGTH, ARROW_SELECTION_THICKNESS_DELTA, SELECTION_OVERLAY_COLOR } from "@/app/constants";
import { pamet } from "@/app/facade";
import { BaseCanvasView } from "@/views/note/BaseCanvasView";
import { ArrowViewState, BezierCurve } from "@/views/arrow/ArrowViewState";

const selectionColor = SELECTION_OVERLAY_COLOR;

export class ArrowCanvasView extends BaseCanvasView {
    get arrowViewState(): ArrowViewState {
        return this.elementViewState as ArrowViewState;
    }

    _renderArrowHead(context: CanvasRenderingContext2D, curves: BezierCurve[]) {
        // Get the inclination of the path near its end to determine the arrow
        // head direction. We use a point near the tip — intentionally NOT the
        // tangent at the endpoint, because the last bezier control point is
        // axis-aligned to the note anchor, which would make the arrow head
        // always perpendicular to it.
        let inclinationPoint = this.arrowViewState.headAnglePoint;
        let endPoint = curves[curves.length - 1][3];

        let dx = endPoint.x - inclinationPoint.x;
        let dy = endPoint.y - inclinationPoint.y;
        let len = Math.sqrt(dx * dx + dy * dy);
        if (len < 1e-6) {
            // Very short curve — fall back to last control point direction
            let [, , P2, P3] = curves[curves.length - 1];
            dx = P3.x - P2.x;
            dy = P3.y - P2.y;
            len = Math.sqrt(dx * dx + dy * dy);
        }
        if (len > 0) {
            dx /= len;
            dy /= len;
        }

        // The hand base is ARROW_HAND_LENGTH back along the approach direction
        let baseX = endPoint.x - dx * ARROW_HAND_LENGTH;
        let baseY = endPoint.y - dy * ARROW_HAND_LENGTH;

        // Rotate the base point ±25° around the endpoint to get the two hands
        let cos = Math.cos(ARROW_HAND_ANGLE_RAD);
        let sin = Math.sin(ARROW_HAND_ANGLE_RAD);
        let bx = baseX - endPoint.x;
        let by = baseY - endPoint.y;

        let hand1x = endPoint.x + cos * bx - sin * by;
        let hand1y = endPoint.y + sin * bx + cos * by;
        let hand2x = endPoint.x + cos * bx + sin * by;
        let hand2y = endPoint.y - sin * bx + cos * by;

        context.beginPath();
        context.moveTo(endPoint.x, endPoint.y);
        context.lineTo(hand1x, hand1y);
        context.moveTo(endPoint.x, endPoint.y);
        context.lineTo(hand2x, hand2y);
        context.stroke();
        context.closePath();
    }

    _drawArrowBody(context: CanvasRenderingContext2D, path: Path2D) {
        context.stroke(path);
    }

    render(context: CanvasRenderingContext2D) {
        let arrow = this.arrowViewState.arrow();
        let curves: BezierCurve[] | undefined;
        let path: Path2D | undefined;
        try {
            curves = this.arrowViewState.bezierCurveParams;
            path = this.arrowViewState.path2d;
        } catch (e) {
            return; // anchor notes missing — skip this arrow
        }
        if (!curves || curves.length === 0 || !path) return;

        context.strokeStyle = pamet.themeManager.canvasColor(arrow.colorRole);
        context.lineWidth = arrow.thickness;
        this._drawArrowBody(context, path);
        this._renderArrowHead(context, curves);
    }

    renderSelectionOverlay(context: CanvasRenderingContext2D) {
        let arrow = this.arrowViewState.arrow();
        let curves: BezierCurve[] | undefined;
        let path: Path2D | undefined;
        try {
            curves = this.arrowViewState.bezierCurveParams;
            path = this.arrowViewState.path2d;
        } catch (e) {
            return;
        }
        if (!curves || curves.length === 0 || !path) return;

        context.strokeStyle = selectionColor;
        context.lineWidth = arrow.thickness + ARROW_SELECTION_THICKNESS_DELTA;
        this._drawArrowBody(context, path);
        this._renderArrowHead(context, curves);
    }
}
