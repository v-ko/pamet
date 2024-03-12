import { Arrow, ArrowAnchorType, ArrowData } from '../../model/Arrow';
import { computed, makeObservable, observable } from 'mobx';
import { NoteViewState } from '../note/NoteViewState';
import { getLogger } from '../../fusion/logging';
import { Point2D } from '../../util/Point2D';
import { Rectangle } from '../../util/Rectangle';
import { approximateMidpointOfBezierCurve } from '../../util';
import { PageChildViewState } from '../canvas/PageChildViewState';
import paper from 'paper';

let log = getLogger('ArrowViewState');


// Each curve has:
// start_point, first_control_point, second_control point, end_point
export type BezierCurve = [Point2D, Point2D, Point2D, Point2D]


let CP_BASE_DISTANCE = 80;
let CP_DIST_SEGMENT_ADJUST_K = 0.1;


function specialSigmoid(x: number): number {
    return 1 / (1 + Math.exp(-x / (CP_BASE_DISTANCE / 2) + 5));
}

export class ArrowViewState extends PageChildViewState {
    _arrowData: ArrowData;
    headAnchorNoteViewState: NoteViewState | null = null;
    tailAnchorNoteViewState: NoteViewState | null = null;
    pathCalculationPrecision: number = 1;
    _paperPath: paper.Path | null = null;

    constructor(arrow: Arrow, headAnchorNoteViewState: NoteViewState | null, tailAnchorNoteViewState: NoteViewState | null, pathCalculationPrecision: number) {
        super();

        this._arrowData = arrow.data();
        this.headAnchorNoteViewState = headAnchorNoteViewState;
        this.tailAnchorNoteViewState = tailAnchorNoteViewState;

        makeObservable(this, {
            _arrowData: observable,
            arrow: computed,
            headAnchorNoteViewState: observable,
            tailAnchorNoteViewState: observable,
            bezierCurveParams: computed,
            bezierCurveArrayMidpoints: computed,
            paperPath: computed,
        });
    }
    get arrow(): Arrow {
        return new Arrow(this._arrowData);
    }
    pageChild(): Arrow {
        return this.arrow;
    }
    updateFromArrow(arrow: Arrow, headAnchorNoteViewState: NoteViewState | null, tailAnchorNoteViewState: NoteViewState | null) {
        // Object.keys(this._data).forEach(key => {
        //     this._data[key] = arrow._data[key];
        // });
        this._arrowData = arrow.data();
        this.headAnchorNoteViewState = headAnchorNoteViewState;
        this.tailAnchorNoteViewState = tailAnchorNoteViewState;
    }

    get bezierCurveParams(): BezierCurve[] {
        let arrow = this.arrow

        // Determine the tail anchor position
        let tailAnchorPos: Point2D;
        if (arrow.hasTailAnchor()) {
            if (this.tailAnchorNoteViewState) {
                if (arrow.tail_anchor) {
                    tailAnchorPos = this.tailAnchorNoteViewState.note.arrowAnchor(arrow.tailAnchorType);
                } else {
                    throw new Error('Tail anchor is set, but tail anchor type is not');
                }
            } else {
                throw new Error('Tail anchor is set, but tail anchor note view state is not');
            }
        } else if (arrow.tail_point) {
            tailAnchorPos = arrow.tail_point;
        } else {
            throw new Error('Neither tail anchor nor tail point are set');
        }

        // Determine the head anchor position
        let headAnchorPos: Point2D;
        if (arrow.hasHeadAnchor()) {
            if (this.headAnchorNoteViewState) {
                if (arrow.head_anchor) {
                    headAnchorPos = this.headAnchorNoteViewState.note.arrowAnchor(arrow.headAnchorType);
                } else {
                    throw new Error('Head anchor is set, but head anchor type is not');
                }
            } else {
                throw new Error('Head anchor is set, but head anchor note view state is not');
            }
        } else if (arrow.head_point) {
            headAnchorPos = arrow.head_point;
        } else {
            throw new Error('Neither head anchor nor head point are set');
        }

        if (tailAnchorPos.equals(headAnchorPos)) {
            return [];
        }

        let curves = this.calculateBezierCurveParams(tailAnchorPos, headAnchorPos);
        return curves;
    }


    calculalteTerminalControlPoint(terminalPoint: Point2D, adjacentPoint: Point2D, controlPointDistance: number, anchorType: ArrowAnchorType): Point2D {
        if (anchorType === ArrowAnchorType.NONE) {
            let k = controlPointDistance / terminalPoint.distanceTo(adjacentPoint);
            return terminalPoint.add(adjacentPoint.subtract(terminalPoint).multiply(k));
        } else if (anchorType === ArrowAnchorType.MID_LEFT) {
            return terminalPoint.subtract(new Point2D(controlPointDistance, 0));
        } else if (anchorType === ArrowAnchorType.TOP_MID) {
            return terminalPoint.subtract(new Point2D(0, controlPointDistance));
        } else if (anchorType === ArrowAnchorType.MID_RIGHT) {
            return terminalPoint.add(new Point2D(controlPointDistance, 0));
        } else if (anchorType === ArrowAnchorType.BOTTOM_MID) {
            return terminalPoint.add(new Point2D(0, controlPointDistance));
        } else {
            throw new Error('Invalid anchor type');
        }
    }

    inferArrowAnchorType(adjacentPoint: Point2D, noteRect: Rectangle): ArrowAnchorType {
        // If the adjacent point is to the left or right - set a side anchor
        if (adjacentPoint.x < noteRect.left()) {
            return ArrowAnchorType.MID_LEFT;
        } else if (adjacentPoint.x > noteRect.right()) {
            return ArrowAnchorType.MID_RIGHT;
        } else {
            // If the point is directly above or below the note - set a
            // top/bottom anchor
            if (adjacentPoint.y < noteRect.top()) {
                return ArrowAnchorType.TOP_MID;
            } else if (adjacentPoint.y > noteRect.bottom()) {
                return ArrowAnchorType.BOTTOM_MID;
            } else {
                // If the adjacent point is inside the note_rect - set either
                // a top or bottom anchor (arbitrary, its ugly either way)
                if (adjacentPoint.y < noteRect.center().y) {
                    return ArrowAnchorType.TOP_MID;
                } else {
                    return ArrowAnchorType.BOTTOM_MID;
                }
            }
        }
    }

    cpDistanceForSegment(firstPoint: Point2D, secondPoint: Point2D): number {
        let dist = firstPoint.distanceTo(secondPoint);
        return (specialSigmoid(dist) * CP_BASE_DISTANCE + CP_DIST_SEGMENT_ADJUST_K * dist);
    }

    calculateBezierCurveParams(tailPoint: Point2D, headPoint: Point2D): BezierCurve[] {
        let arrow = this.arrow;
        let curves: BezierCurve[] = [];
        // Determine the secondPoint of the first curve
        // That's either the first mid point, or the head point (if no midpoints)
        let secondPoint: Point2D;
        if (arrow.mid_points.length) {
            secondPoint = arrow.mid_points[0];
        } else if (headPoint) {
            secondPoint = headPoint;
        } else {
            throw new Error('Neither mid points nor head point are set');
        }

        // If the anchor type for the tail is AUTO - infer it
        let tailAnchorType: ArrowAnchorType;
        if (arrow.hasTailAnchor() && arrow.tailAnchorType === ArrowAnchorType.AUTO) {
            tailAnchorType = this.inferArrowAnchorType(secondPoint, this.tailAnchorNoteViewState!.note.rect());
        } else {
            tailAnchorType = arrow.tailAnchorType;
        }

        let controlPointDistance = this.cpDistanceForSegment(tailPoint, secondPoint);
        let firstCp = this.calculalteTerminalControlPoint(tailPoint, secondPoint, controlPointDistance, tailAnchorType);

        // Add the second control point for the first curve
        // and all the middle curves (if any), excluding the last control point
        let prevPoint: Point2D = tailPoint;
        for (let idx = 0; idx < arrow.mid_points.length; idx++) {
            let currentPoint = arrow.mid_points[idx];

            /// If we're at the last point
            let nextPoint: Point2D;
            if (idx + 1 === arrow.mid_points.length) {
                nextPoint = headPoint;
            } else {
                nextPoint = arrow.mid_points[idx + 1];
            }

            // Calculate alpha (see the schematic for details)
            let a = currentPoint.distanceTo(nextPoint);
            let b = prevPoint.distanceTo(currentPoint);
            let dA = prevPoint.subtract(currentPoint);
            let dB = nextPoint.subtract(currentPoint);
            let gamma = Math.atan2(dA.y, dA.x);
            let theta = Math.atan2(dB.y, dB.x);
            if (gamma < 0) {
                gamma += Math.PI * 2;
            }
            if (theta < 0) {
                theta += Math.PI * 2;
            }
            let beta = (Math.PI * 2 + theta - gamma) % (Math.PI * 2);
            let alpha = Math.PI / 2 - beta / 2;  // In radians 90 - beta/2

            controlPointDistance = this.cpDistanceForSegment(prevPoint, currentPoint);

            // Calculate the second control point for the first curve
            if (b === 0) {
                b = 0.0001;
            }
            let k = controlPointDistance / b;
            let zPrim = currentPoint.add(prevPoint.subtract(currentPoint).multiply(k));
            let secondControlPoint = zPrim.rotated(alpha, currentPoint);

            // Save the params
            curves.push([prevPoint, firstCp, secondControlPoint, currentPoint]);

            // Calculate the first control point for the second curve
            // (mirrors the second cp of the last curve)
            controlPointDistance = this.cpDistanceForSegment(currentPoint, nextPoint);
            if (a === 0) {
                a = 0.0001;
            }
            k = controlPointDistance / a;
            let qPrim = currentPoint.add(nextPoint.subtract(currentPoint).multiply(k));
            firstCp = qPrim.rotated(-alpha, currentPoint);

            prevPoint = currentPoint;
        }

        // If the head anchor type is AUTO - infer it
        let headAnchorType: ArrowAnchorType;
        if (arrow.hasHeadAnchor() && arrow.headAnchorType === ArrowAnchorType.AUTO) {
            headAnchorType = this.inferArrowAnchorType(secondPoint, this.headAnchorNoteViewState!.note.rect());
        } else {
            headAnchorType = arrow.headAnchorType;
        }

        // Add the second control point for the last curve
        let lastControlPoint: Point2D;
        if (!arrow.mid_points.length) {
            lastControlPoint = this.calculalteTerminalControlPoint(headPoint, tailPoint, controlPointDistance, headAnchorType);
        } else {
            lastControlPoint = this.calculalteTerminalControlPoint(headPoint, secondPoint, controlPointDistance, headAnchorType);
        }

        curves.push([prevPoint, firstCp, lastControlPoint, headPoint]);
        return curves;
    }

    get bezierCurveArrayMidpoints(): Point2D[] {
        let curves = this.bezierCurveParams;
        let midPoints: Point2D[] = [];


        for (let curve of curves) {
            let midPoint = approximateMidpointOfBezierCurve(curve[0], curve[1], curve[2], curve[3], this.pathCalculationPrecision);
            midPoints.push(midPoint);
        }
        return midPoints;
    }

    // *** TUK *** !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    edgePointPos(edgeIndex: number): Point2D {
        /** Returns the edge point position for the given index
         * Those include the tail, midpoints and head
         *
         * The indeces are not integers, since the suggested new edge points
         * are denoted with non-whole indices (e.g. 0.5, 1.5 etc.).
         * More over the tail index is 0, and the head index is the last one.
         */

        let point: Point2D;
        if (edgeIndex % 1 === 0) {
            if (edgeIndex === 0) {
                return this.bezierCurveParams[0][0];
            } else {
                let curveIdx = Math.floor(edgeIndex - 1);
                let curve = this.bezierCurveParams[curveIdx];
                point = curve[3];
                return point.copy();
            }
        } else {
            point = this.bezierCurveArrayMidpoints[Math.floor(edgeIndex)];
            return point.copy();
        }
    }

    edgeAt(position: Point2D): number | null {
        let realPos = position;
        let indices = this.arrow.allEdgeIndices();
        for (let idx of indices) {
            let point = this.edgePointPos(idx);

            let radius: number;
            if (idx % 1 === 0) {
                radius = 5;
            } else {
                radius = 10;
            }
            if (point.distanceTo(realPos) <= radius) {
                return idx;
            }
        }
        return null;
    }


    get paperPath(): paper.Path {
        if (this._paperPath !== null) {
            this._paperPath.remove();
        }
        this._paperPath = new paper.Path();
        let curves = this.bezierCurveParams;
        for (let curve of curves) {
            this._paperPath.moveTo(curve[0]);
            this._paperPath.cubicCurveTo(curve[1], curve[2], curve[3]);
        }
        return this._paperPath;
    }

    intersectsCircle(center: Point2D, radius: number): boolean {
        let path = this.paperPath;
        let circlePath = new paper.Path.Circle(center, radius);
        let intersects = path.intersects(circlePath);
        circlePath.remove();
        return intersects;
    }

    intersectsRect(rect: Rectangle): boolean {
        let path = this.paperPath;
        let pRect = new paper.Rectangle(rect.topLeft(), rect.bottomRight());
        let pItem = new paper.Path.Rectangle(pRect);
        let intersects = path.intersects(pItem) || path.isInside(pRect);
        pItem.remove();
        return intersects;
    }
}
