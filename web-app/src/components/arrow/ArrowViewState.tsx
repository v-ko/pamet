import { Arrow, arrowAnchorPosition, ArrowAnchorOnNoteType, ArrowData } from '../../model/Arrow';
import { computed, makeObservable, observable, toJS } from 'mobx';
import { NoteViewState } from '../note/NoteViewState';
import { getLogger } from 'fusion/logging';
import { Point2D } from '../../util/Point2D';
import { Rectangle } from '../../util/Rectangle';
import { approximateMidpointOfBezierCurve } from '../../util';
import { ElementViewState } from '../page/ElementViewState';
import paper from 'paper';
import { ARROW_CONTROL_POINT_RADIUS, POTENTIAL_CONTROL_POINT_RADIUS } from '../../core/constants';

let log = getLogger('ArrowViewState');


// Each curve has:
// start_point, first_control_point, second_control point, end_point
// ! Note that bezier curve control points != arrow CPs in the interface
export type BezierCurve = [Point2D, Point2D, Point2D, Point2D]


let CP_BASE_DISTANCE = 80;
let CP_DIST_SEGMENT_ADJUST_K = 0.1;


function specialSigmoid(x: number): number {
    return 1 / (1 + Math.exp(-x / (CP_BASE_DISTANCE / 2) + 5));
}

export class ArrowViewState extends ElementViewState {
    _arrowData!: ArrowData;
    headAnchorNoteViewState: NoteViewState | null = null;
    tailAnchorNoteViewState: NoteViewState | null = null;
    pathCalculationPrecision: number = 1;
    _paperPath: paper.Path | null = null;

    constructor(arrow: Arrow, headAnchorNoteViewState: NoteViewState | null, tailAnchorNoteViewState: NoteViewState | null) {
        super();

        this.updateFromArrow(arrow, headAnchorNoteViewState, tailAnchorNoteViewState);

        makeObservable(this, {
            _arrowData: observable,
            _arrow: computed,
            headAnchorNoteViewState: observable,
            tailAnchorNoteViewState: observable,
            bezierCurveParams: computed,
            bezierCurveArrayMidpoints: computed,
            paperPath: computed,
        });
    }

    get _arrow(): Arrow {
        let arrowData = toJS(this._arrowData) as ArrowData;
        return new Arrow(arrowData);
        // let arrow = pamet.findOne({id: this._arrowData.id});
        // if (arrow === undefined) {
        //     throw Error('Arrow not found');
        // }
        // return arrow as Arrow;
    }
    arrow(): Arrow {
        return this._arrow;
    }
    element(): Arrow {
        return this.arrow();
    }
    updateFromArrow(arrow: Arrow, headAnchorNoteViewState: NoteViewState | null, tailAnchorNoteViewState: NoteViewState | null) {
        // console.log('updateFromArrow', arrow, headAnchorNoteViewState, tailAnchorNoteViewState);
        this._arrowData = arrow.data();

        this.headAnchorNoteViewState = headAnchorNoteViewState;
        this.tailAnchorNoteViewState = tailAnchorNoteViewState;
    }

    get bezierCurveParams(): BezierCurve[] {
        let arrow = this.arrow()
        let curves: BezierCurve[] = [];

        // Calculate head and tail static positions and anchor types
        let tailPoint: Point2D;
        let headPoint: Point2D;
        let effectiveTailAnchorType: ArrowAnchorOnNoteType;
        let effectiveHeadAnchorType: ArrowAnchorOnNoteType;

        // If both are with fixed coordinates - easy
        if (!arrow.tailAnchoredOnNote && !arrow.headAnchoredOnNote) {
            effectiveTailAnchorType = ArrowAnchorOnNoteType.none;
            effectiveHeadAnchorType = ArrowAnchorOnNoteType.none;

            // If both have anchors and both anchors are Auto and there's no mid-points
            // infer from the geometry of the notes
        } if (arrow.tailAnchoredOnNote && arrow.headAnchoredOnNote &&
            (arrow.headAnchorType === ArrowAnchorOnNoteType.auto) &&
            (arrow.tailAnchorType === ArrowAnchorOnNoteType.auto) &&
            arrow.midPoints.length === 0) {

            // Check tha note view states are present
            if (this.tailAnchorNoteViewState === null) {
                throw Error('Tail anchor is set, but tail anchor note view state is not');
            }
            if (this.headAnchorNoteViewState === null) {
                throw Error('Head anchor is set, but head anchor note view state is not');
            }

            let tailNote = this.headAnchorNoteViewState.note();
            let headNote = this.headAnchorNoteViewState.note();
            let tailRect = tailNote.rect();
            let headRect = headNote.rect();

            let intersectionRect = tailRect.intersection(headRect);
            // If the notes intersect - the arrow would start/and on a same-name anchor
            if (intersectionRect) {
                // if the intersection rectangle is wider than it is tall - the arrow anchors at
                // top-top or bott-bott (depending on the center-y of the note rects)
                if (intersectionRect.width > intersectionRect.height) {
                    if (tailRect.center().y < headRect.center().y) {
                        effectiveTailAnchorType = ArrowAnchorOnNoteType.top_mid;
                        effectiveHeadAnchorType = ArrowAnchorOnNoteType.top_mid;
                    } else {
                        effectiveTailAnchorType = ArrowAnchorOnNoteType.bottom_mid;
                        effectiveHeadAnchorType = ArrowAnchorOnNoteType.bottom_mid;
                    }
                } else {
                    // More intersection on the y axis - the arrow anchors at left-left or right-right
                    if (tailRect.center().x < headRect.center().x) {
                        effectiveTailAnchorType = ArrowAnchorOnNoteType.mid_left;
                        effectiveHeadAnchorType = ArrowAnchorOnNoteType.mid_left;
                    } else {
                        effectiveTailAnchorType = ArrowAnchorOnNoteType.mid_right;
                        effectiveHeadAnchorType = ArrowAnchorOnNoteType.mid_right;
                    }
                }
            } else {
                // If there's no intersection - if the notes are above one another
                // the arrow should be top-bottom/bottom-top
                if (tailRect.center().y < headRect.center().y) {
                    effectiveTailAnchorType = ArrowAnchorOnNoteType.top_mid;
                    effectiveHeadAnchorType = ArrowAnchorOnNoteType.bottom_mid;
                } else {
                    effectiveTailAnchorType = ArrowAnchorOnNoteType.bottom_mid;
                    effectiveHeadAnchorType = ArrowAnchorOnNoteType.top_mid;
                }
            }

            // If one of the anchors is auto and there is at least one midpoint
        } else if ( // Only one of the anchors is possibly auto
            (arrow.midPoints.length > 0)) {
            // TODO: use the inferArrowAnchor func from adjacent point using the adj. midpoint
            // where the anchor is on a note
            let tailAdjacentPoint = arrow.midPoints[0];
            let headAdjacentPoint = arrow.midPoints[arrow.midPoints.length - 1];

            effectiveTailAnchorType = this.inferTailAnchorType(tailAdjacentPoint);
            effectiveHeadAnchorType = this.inferHeadAnchorType(headAdjacentPoint);

        } else if (  // Only one of the anchors is possibly auto
            (arrow.midPoints.length === 0)) {
            // if one of the anchors is auto and there's no midpoints
            // TODO: Infer from the adjacent point (using the non-auto anchor as adjacent)
            // If the tail is auto - get the head point and infer the tail anchor
            if (arrow.tailAnchorType === ArrowAnchorOnNoteType.auto) {
                // If the head has a fixed position
                if (arrow.headPoint) {
                    headPoint = arrow.headPoint;
                } else {
                    headPoint = arrowAnchorPosition(this.headAnchorNoteViewState!.note(), arrow.headAnchorType);
                }
                effectiveTailAnchorType = this.inferTailAnchorType(headPoint);
                effectiveHeadAnchorType = arrow.headAnchorType;
            } else if (arrow.headAnchorType === ArrowAnchorOnNoteType.auto) {
                // If the tail has a fixed position
                if (arrow.tailPoint) {
                    tailPoint = arrow.tailPoint;
                } else {
                    tailPoint = arrowAnchorPosition(this.tailAnchorNoteViewState!.note(), arrow.tailAnchorType);
                }
                effectiveHeadAnchorType = this.inferHeadAnchorType(tailPoint);
                effectiveTailAnchorType = arrow.tailAnchorType;
            } else {
                effectiveHeadAnchorType = arrow.headAnchorType;
                effectiveTailAnchorType = arrow.tailAnchorType;
            }
        } else {
            console.log(this)
            throw Error('No such case2');
        }

        // Calculate the tail and head points
        if (effectiveTailAnchorType === ArrowAnchorOnNoteType.none) {
            tailPoint = arrow.tailPoint!;
        } else {
            tailPoint = arrowAnchorPosition(this.tailAnchorNoteViewState!.note(), effectiveTailAnchorType);
        }

        if (effectiveHeadAnchorType === ArrowAnchorOnNoteType.none) {
            headPoint = arrow.headPoint!;
        } else {
            headPoint = arrowAnchorPosition(this.headAnchorNoteViewState!.note(), effectiveHeadAnchorType);
        }


        // If the head and tail are on the same point with no midpoints - set control points such that the arrow is a loop
        if (arrow.midPoints.length === 0 && tailPoint.equals(headPoint)) {
            let controlPointDistance = CP_BASE_DISTANCE;
            // Set perpendicular control points
            let cp1 = tailPoint.add(new Point2D(controlPointDistance, 0));
            let cp2 = tailPoint.add(new Point2D(0, controlPointDistance));
            curves.push([tailPoint, cp1, cp2, headPoint]);
            return curves;
        }

        // Infer adjacent points in order to calculate the first and last bezier control points
        let tailAdjacentPoint: Point2D;
        let headAdjacentPoint: Point2D;
        if (arrow.midPoints.length > 0) {
            tailAdjacentPoint = arrow.midPoints[0];
            headAdjacentPoint = arrow.midPoints[arrow.midPoints.length - 1];
        } else {
            tailAdjacentPoint = headPoint;
            headAdjacentPoint = tailPoint;
        }

        let controlPointDistance = this.cpDistanceForSegment(tailPoint, tailAdjacentPoint);
        let firstCp = this.headOrTailBezierControlPoint(tailPoint, tailAdjacentPoint, controlPointDistance, effectiveTailAnchorType);

        // Add the second control point for the first curve
        // and all the middle curves (if any), excluding the last control point
        let prevPoint: Point2D = tailPoint;
        for (let idx = 0; idx < arrow.midPoints.length; idx++) {
            let currentPoint = arrow.midPoints[idx];

            /// If we're at the last point
            let nextPoint: Point2D;
            if (idx + 1 === arrow.midPoints.length) {
                nextPoint = headPoint;
            } else {
                nextPoint = arrow.midPoints[idx + 1];
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

        // Add the second control point for the last curve
        let lastControlPoint = this.headOrTailBezierControlPoint(headPoint, headAdjacentPoint, controlPointDistance, effectiveHeadAnchorType);

        curves.push([prevPoint, firstCp, lastControlPoint, headPoint]);

        return curves;
    }


    headOrTailBezierControlPoint(headOrTailPosition: Point2D, adjacentPoint: Point2D, controlPointDistance: number, effectiveAnchorType: ArrowAnchorOnNoteType): Point2D {

        if (effectiveAnchorType === ArrowAnchorOnNoteType.none) {
            let k = controlPointDistance / headOrTailPosition.distanceTo(adjacentPoint);
            return headOrTailPosition.add(adjacentPoint.subtract(headOrTailPosition).multiply(k));
        } else if (effectiveAnchorType === ArrowAnchorOnNoteType.mid_left) {
            return headOrTailPosition.subtract(new Point2D(controlPointDistance, 0));
        } else if (effectiveAnchorType === ArrowAnchorOnNoteType.top_mid) {
            return headOrTailPosition.subtract(new Point2D(0, controlPointDistance));
        } else if (effectiveAnchorType === ArrowAnchorOnNoteType.mid_right) {
            return headOrTailPosition.add(new Point2D(controlPointDistance, 0));
        } else if (effectiveAnchorType === ArrowAnchorOnNoteType.bottom_mid) {
            return headOrTailPosition.add(new Point2D(0, controlPointDistance));
        } else {
            throw Error('Effective type should have been inferred (!=auto). Type: ' + effectiveAnchorType);
        }
    }

    inferTailAnchorType(secondPoint: Point2D): ArrowAnchorOnNoteType {
        /** Only refactored out to DRY the code a bit */
        let arrow = this.arrow();
        let effectiveTailAnchorType: ArrowAnchorOnNoteType;
        if (arrow.tailAnchorType === ArrowAnchorOnNoteType.auto) {
            if (this.tailAnchorNoteViewState === null) {
                throw Error('Tail anchor type is AUTO, but no head note view state is set');
            }
            effectiveTailAnchorType = inferArrowAnchorType(secondPoint, this.tailAnchorNoteViewState.note().rect());
        } else {
            effectiveTailAnchorType = arrow.tailAnchorType;
        }

        return effectiveTailAnchorType
    }

    inferHeadAnchorType(secondPoint: Point2D): ArrowAnchorOnNoteType {
        /** Only refactored out to DRY the code a bit */
        let arrow = this.arrow();
        let effectiveHeadAnchorType: ArrowAnchorOnNoteType;
        if (arrow.headAnchorType === ArrowAnchorOnNoteType.auto) {
            if (this.headAnchorNoteViewState === null) {
                throw Error('Head anchor type is AUTO, but no head note view state is set');
            }
            effectiveHeadAnchorType = inferArrowAnchorType(secondPoint, this.headAnchorNoteViewState.note().rect());
        } else {
            effectiveHeadAnchorType = arrow.headAnchorType;
        }

        return effectiveHeadAnchorType
    }

    cpDistanceForSegment(firstPoint: Point2D, secondPoint: Point2D): number {
        let dist = firstPoint.distanceTo(secondPoint);
        return (specialSigmoid(dist) * CP_BASE_DISTANCE + CP_DIST_SEGMENT_ADJUST_K * dist);
    }

    get bezierCurveArrayMidpoints(): Point2D[] {
        let curves = this.bezierCurveParams;
        let midPoints: Point2D[] = [];

        let precision = 1;

        for (let curve of curves) {
            let midPoint = approximateMidpointOfBezierCurve(curve[0], curve[1], curve[2], curve[3], precision);
            midPoints.push(midPoint);
        }
        return midPoints;
    }

    controlPointPosition(controlPointIndex: number): Point2D {
        /** Returns the control point position for the given index
         * Those include the tail, midpoints and head
         *
         * The indeces are not integers, since the suggested new control points
         * are denoted with non-whole indices (e.g. 0.5, 1.5 etc.).
         * More over the tail index is 0, and the head index is the last one.
         */

        let point: Point2D;
        if (controlPointIndex % 1 === 0) {
            if (controlPointIndex === 0) {
                return this.bezierCurveParams[0][0];
            } else {
                let curveIdx = Math.floor(controlPointIndex - 1);
                let curve = this.bezierCurveParams[curveIdx];
                point = curve[3];
                return point.copy();
            }
        } else {
            point = this.bezierCurveArrayMidpoints[Math.floor(controlPointIndex)];
            return point.copy();
        }
    }

    controlPointAt(realPosition: Point2D): number | null {
        /** Returns the control point index at the given real position
         * if there's a control point there or a suggested one.
         */
        let arrow = this.arrow();
        // Find the closest control point
        let closestControlPointIndex = null;
        let closestControlPointDistance = Infinity;

        // Check the control points
        for (let i of arrow.controlPointIndices()) {
            let controlPoint = this.controlPointPosition(i);
            let distance = controlPoint.distanceTo(realPosition);
            // Skip if outside the circle
            if (distance > ARROW_CONTROL_POINT_RADIUS) {
                continue;
            }
            if (distance < closestControlPointDistance) {
                closestControlPointDistance = distance;
                closestControlPointIndex = i;
            }
        }

        // Check the suggested control points
        for (let i of arrow.potentialControlPointIndices()) {
            let controlPoint = this.controlPointPosition(i);
            let distance = controlPoint.distanceTo(realPosition);
            // Skip if outside the circle
            if (distance > POTENTIAL_CONTROL_POINT_RADIUS) {
                continue;
            }
            if (distance < closestControlPointDistance) {
                closestControlPointDistance = distance;
                closestControlPointIndex = i;
            }
        }

        return closestControlPointIndex
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


export function inferArrowAnchorType(adjacentPoint: Point2D, noteRect: Rectangle): ArrowAnchorOnNoteType {
    // If the adjacent point is to the left or right - set a side anchor
    if (adjacentPoint.x < noteRect.left()) {
        return ArrowAnchorOnNoteType.mid_left;
    } else if (adjacentPoint.x > noteRect.right()) {
        return ArrowAnchorOnNoteType.mid_right;
    } else { // If the point is directly above or below the note
        // set a top/bottom anchor
        if (adjacentPoint.y < noteRect.top()) {
            return ArrowAnchorOnNoteType.top_mid;
        } else if (adjacentPoint.y > noteRect.bottom()) {
            return ArrowAnchorOnNoteType.bottom_mid;
        } else {
            // If the adjacent point is inside the note_rect - set either
            // a top or bottom anchor (arbitrary, its ugly either way)
            if (adjacentPoint.y < noteRect.center().y) {
                return ArrowAnchorOnNoteType.top_mid;
            } else {
                return ArrowAnchorOnNoteType.bottom_mid;
            }
        }
    }
}
