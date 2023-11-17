import { Arrow, ArrowAnchorType } from '../model/Arrow';
import { computed, makeObservable, observable } from 'mobx';
import { NoteViewState } from './note/NoteViewState';
import { getLogger } from '../fusion/logging';
import { degreesToRadians } from '../fusion/util';
import { Point2D, PointData } from '../util/Point2D';
import { Rectangle } from '../util/Rectangle';
import { approximateMidpointOfBezierCurve } from '../util';

let log = getLogger('ArrowViewState');


// Each curve has:
// start_point, first_control_point, second_control point, end_point
export type BezierCurve = [Point2D, Point2D, Point2D, Point2D]


let CONTROL_POINT_DEBUG_VISUALS = false;
let TAIL = 'tail';
let HEAD = 'head';
let ARROW_HAND_LENGTH = 20;
let ARROW_HAND_ANGLE = degreesToRadians(25);
let CP_BASE_DISTANCE = 80;
let CP_DIST_SEGMENT_ADJUST_K = 0.1;


function specialSigmoid(x: number): number {
    return 1 / (1 + Math.exp(-x / (CP_BASE_DISTANCE / 2) + 5));
}

export class ArrowViewState extends Arrow {
    headAnchorNoteViewState: NoteViewState | null = null;
    tailAnchorNoteViewState: NoteViewState | null = null;
    pathCalculationPrecision: number = 1;

    constructor(arrow: Arrow, headAnchorNoteViewState: NoteViewState | null, tailAnchorNoteViewState: NoteViewState | null, pathCalculationPrecision: number) {
        super(arrow._data);
        this.headAnchorNoteViewState = headAnchorNoteViewState;
        this.tailAnchorNoteViewState = tailAnchorNoteViewState;

        makeObservable(this, {
            _data: observable,
            headAnchorNoteViewState: observable,
            tailAnchorNoteViewState: observable,
            bezierCurveParams: computed,
            bezierCurveArrayMidpoints: computed,
        });
    }

    updateFromArrow(arrow: Arrow, headAnchorNoteViewState: NoteViewState | null, tailAnchorNoteViewState: NoteViewState | null) {
        Object.keys(this._data).forEach(key => {
            this._data[key] = arrow._data[key];
        });
        this.headAnchorNoteViewState = headAnchorNoteViewState;
        this.tailAnchorNoteViewState = tailAnchorNoteViewState;
    }

    get bezierCurveParams(): BezierCurve[] {
        // let state = this;

        //         if state.has_tail_anchor():
        //             tail_note = pamet.note(state.page_id, state.tail_note_id)
        //             nv_state = self.map_page_view.get_note_view_state_for_note_gid(
        //                 tail_note.gid())
        //             if not nv_state:
        //                 raise Exception
        //             if state.tail_anchor:
        //                 tail_anchor_pos = nv_state.arrow_anchor(state.tail_anchor_type)
        //             else:
        //                 raise NotImplementedError
        //         elif state.tail_point:
        //             tail_anchor_pos = state.tail_point
        //         else:
        //             # there should be either a position or an anchor set
        //             # if on init there's acceptable cases without - just return here
        //             return
        //             raise Exception

        // Determine the tail anchor position
        let tailAnchorPos: Point2D;
        if (this.hasTailAnchor()) {
            if (this.tailAnchorNoteViewState) {
                if (this.tail_anchor) {
                    tailAnchorPos = this.tailAnchorNoteViewState.arrowAnchor(this.tailAnchorType);
                } else {
                    throw new Error('Tail anchor is set, but tail anchor type is not');
                }
            } else {
                throw new Error('Tail anchor is set, but tail anchor note view state is not');
            }
        } else if (this.tail_point) {
            tailAnchorPos = this.tail_point;
        } else {
            throw new Error('Neither tail anchor nor tail point are set');
        }

        //         if state.head_note_id:
        //             head_note = pamet.note(state.page_id, state.head_note_id)
        //             nv_state = self.map_page_view.get_note_view_state_for_note_gid(
        //                 head_note.gid())
        //             if not nv_state:
        //                 raise Exception
        //             if state.head_anchor:
        //                 head_anchor_pos = nv_state.arrow_anchor(state.head_anchor_type)
        //             else:
        //                 raise NotImplementedError
        //         elif state.head_point:
        //             head_anchor_pos = state.head_point
        //         else:
        //             # there should be either a position or an anchor set
        //             # if on init there's acceptable cases without - just return here
        //             return

        // Determine the head anchor position
        let headAnchorPos: Point2D;
        if (this.hasHeadAnchor()) {
            if (this.headAnchorNoteViewState) {
                if (this.head_anchor) {
                    headAnchorPos = this.headAnchorNoteViewState.arrowAnchor(this.headAnchorType);
                } else {
                    throw new Error('Head anchor is set, but head anchor type is not');
                }
            } else {
                throw new Error('Head anchor is set, but head anchor note view state is not');
            }
        } else if (this.head_point) {
            headAnchorPos = this.head_point;
        } else {
            throw new Error('Neither head anchor nor head point are set');
        }

        //         if tail_anchor_pos == head_anchor_pos:
        //             self._cached_path = None
        //             return

        if (tailAnchorPos.equals(headAnchorPos)) {
            return [];
        }

        //         if state.line_function_name == BEZIER_CUBIC:
        //             curves = self.bezier_cubic_curves_params(tail_anchor_pos,
        //                                                      head_anchor_pos)
        //             if not curves:
        //                 raise Exception

        //             self._cached_curves = curves

        //             start_point = curves[0][0]
        //             start_point = QPointF(*start_point.as_tuple())
        //             self._cached_path = QPainterPath(start_point)
        //             # curves.extend(reversed([reversed(c) for c in curves]))
        //             for first_point, first_cp, second_cp, second_point in curves:
        //                 first_point = QPointF(*first_point.as_tuple())
        //                 first_cp = QPointF(*first_cp.as_tuple())
        //                 second_cp = QPointF(*second_cp.as_tuple())
        //                 second_point = QPointF(*second_point.as_tuple())

        //                 self._cached_path.cubicTo(first_cp, second_cp, second_point)

        //             # Add the same path reversed in order to have proper filling and
        //             # intersections (otherwise it draws a start-end line to close the
        //             # polygon)
        //             self._cached_path.addPath(self._cached_path.toReversed())
        //         else:
        //             raise NotImplementedError
        let curves = this.calculateBezierCurveParams(tailAnchorPos, headAnchorPos);
        return curves;
    }


    //     def calculate_terminal_cp(self, terminal_point: Point2D,
    //                               adjacent_point: Point2D,
    //                               control_point_distance: float,
    //                               anchor_type: ArrowAnchorType):
    //         if anchor_type == ArrowAnchorType.NONE:
    //             k = control_point_distance / terminal_point.distance_to(
    //                 adjacent_point)
    //             return terminal_point + (adjacent_point - terminal_point) * k
    //         elif anchor_type == ArrowAnchorType.MID_LEFT:
    //             return terminal_point - Point2D(control_point_distance, 0)
    //         elif anchor_type == ArrowAnchorType.TOP_MID:
    //             return terminal_point - Point2D(0, control_point_distance)
    //         elif anchor_type == ArrowAnchorType.MID_RIGHT:
    //             return terminal_point + Point2D(control_point_distance, 0)
    //         elif anchor_type == ArrowAnchorType.BOTTOM_MID:
    //             return terminal_point + Point2D(0, control_point_distance)
    //         else:
    //             raise Exception

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

    //     def infer_arrow_anchor_type(self, adjacent_point: Point2D,
    //                                 note_rect: Rectangle):
    //         # If the adjacent point is to the left or right - set a side anchor
    //         if adjacent_point.x() < note_rect.left():
    //             return ArrowAnchorType.MID_LEFT
    //         elif adjacent_point.x() > note_rect.right():
    //             return ArrowAnchorType.MID_RIGHT
    //         else:
    //             # If the point is directly above or below the note - set a
    //             # top/bottom anchor
    //             if adjacent_point.y() < note_rect.top():
    //                 return ArrowAnchorType.TOP_MID
    //             elif adjacent_point.y() > note_rect.bottom():
    //                 return ArrowAnchorType.BOTTOM_MID
    //             else:
    //                 # If the adjacent point is inside the note_rect - set either
    //                 # a top or bottom anchor (arbitrary, its ugly either way)
    //                 if adjacent_point.y() < note_rect.center():
    //                     return ArrowAnchorType.TOP_MID
    //                 else:
    //                     return ArrowAnchorType.BOTTOM_MID

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


    //     def cp_distance_for_segment(self, first_point, second_point):
    //         dist = first_point.distance_to(second_point)

    //         return (special_sigmoid(dist) * CP_BASE_DISTANCE +
    //                 CP_DIST_SEGMENT_ADJUST_K * dist)

    cpDistanceForSegment(firstPoint: Point2D, secondPoint: Point2D): number {
        let dist = firstPoint.distanceTo(secondPoint);
        return (specialSigmoid(dist) * CP_BASE_DISTANCE + CP_DIST_SEGMENT_ADJUST_K * dist);
    }

    calculateBezierCurveParams(tailPoint: Point2D, headPoint: Point2D): BezierCurve[] {
        //     def bezier_cubic_curves_params(
        //         self,
        //         tail_point: Point2D = None,
        //         head_point: Point2D = None
        //     ) -> List[Tuple[Point2D, Point2D, Point2D, Point2D]]:
        //         """ Returns a list of curve parameters. Each set of parameters is a
        //         tuple in the form:
        //         (start_point, first_control_point, second_control point, end_point)
        //         The parameters tail_point and head_point can override the corresponding
        //         internal variables in order to accomodate for anchor position changes.
        //         """
        //         tail_point = tail_point or self.tail_point
        //         head_point = head_point or self.head_point
        //         curves = []
        //         state = self.state()

        let curves: BezierCurve[] = [];
        // let state = this;

        //         # Handle the first control point of the first curve
        //         if state.mid_points:
        //             second_point = state.mid_points[0]
        //         else:
        //             second_point = head_point

        // Determine the secondPoint of the first curve
        // That's either the first mid point, or the head point (if no midpoints)
        let secondPoint: Point2D;
        if (this.mid_points.length) {
            secondPoint = this.mid_points[0];
        } else if (headPoint) {
            secondPoint = headPoint;
        } else {
            throw new Error('Neither mid points nor head point are set');
        }

        //         # If the anchor type for the tail is AUTO - infer it
        //         if (state.has_tail_anchor()
        //                 and state.tail_anchor_type == ArrowAnchorType.AUTO):
        //             tail_note = pamet.note(state.page_id, state.tail_note_id)
        //             note_view = self.map_page_view.note_widget_by_note_gid(
        //                 tail_note.gid())

        //             tail_anchor_type = self.infer_arrow_anchor_type(
        //                 second_point, note_view.rect())
        //         else:
        //             tail_anchor_type = state.tail_anchor_type

        // If the anchor type for the tail is AUTO - infer it
        let tailAnchorType: ArrowAnchorType;
        if (this.hasTailAnchor() && this.tailAnchorType === ArrowAnchorType.AUTO) {
            tailAnchorType = this.inferArrowAnchorType(secondPoint, this.tailAnchorNoteViewState!.rect);
        } else {
            tailAnchorType = this.tailAnchorType;
        }

        //         control_point_distance = self.cp_distance_for_segment(
        //             tail_point, second_point)

        let controlPointDistance = this.cpDistanceForSegment(tailPoint, secondPoint);

        //         first_cp = self.calculate_terminal_cp(tail_point, second_point,
        //                                               control_point_distance,
        //                                               tail_anchor_type)

        let firstCp = this.calculalteTerminalControlPoint(tailPoint, secondPoint, controlPointDistance, tailAnchorType);

        //         # Add the second control point for the first curve
        //         # and all the middle curves (if any), excluding the last control point
        //         prev_point: Point2D = tail_point
        //         for idx, current_point in enumerate(state.mid_points):
        //             # if idx == 0:
        //             #     prev_point: Point2D = tail_point

        //             # If we're at the last point
        //             if (idx + 1) == len(state.mid_points):
        //                 next_point = head_point
        //                 # should_finish = True
        //             else:
        //                 next_point = state.mid_points[idx + 1]

        // Add the second control point for the first curve
        // and all the middle curves (if any), excluding the last control point
        let prevPoint: Point2D = tailPoint;
        for (let idx = 0; idx < this.mid_points.length; idx++) {
            let currentPoint = this.mid_points[idx];

            /// If we're at the last point
            let nextPoint: Point2D;
            if (idx + 1 === this.mid_points.length) {
                nextPoint = headPoint;
            } else {
                nextPoint = this.mid_points[idx + 1];
            }

            //             # Calculate alpha (see the schematic for details)
            //             a = current_point.distance_to(next_point)
            //             b = prev_point.distance_to(current_point)
            //             # c = prev_point.distance_to(next_point)
            //             # beta = math.acos((a**2 + b**2 - c**2) / (a * b * 2))
            //             dA = prev_point - current_point
            //             dB = next_point - current_point
            //             gamma = math.atan2(dA.y(), dA.x())
            //             theta = math.atan2(dB.y(), dB.x())
            //             if gamma < 0:
            //                 gamma += math.pi * 2
            //             if theta < 0:
            //                 theta += math.pi * 2
            //             beta = (math.pi * 2 + theta - gamma) if gamma > theta else (theta -
            //                                                                         gamma)
            //             alpha = math.pi / 2 - beta / 2  # In radians 90 - beta/2

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

            //             control_point_distance = self.cp_distance_for_segment(
            //                 prev_point, current_point)

            controlPointDistance = this.cpDistanceForSegment(prevPoint, currentPoint);

            //             # Calculate the second control point for the first curve
            //             if b == 0:
            //                 b = 0.0001
            //             k = control_point_distance / b
            //             z_prim: Point2D = current_point + k * (prev_point - current_point)
            //             second_control_point = z_prim.rotated(alpha, current_point)
            //             # second_control_point = z_prim
            //             # second_control_point = current_point + Point2D(50, 50)

            // Calculate the second control point for the first curve
            if (b === 0) {
                b = 0.0001;
            }
            let k = controlPointDistance / b;
            let zPrim = currentPoint.add(prevPoint.subtract(currentPoint).multiply(k));
            let secondControlPoint = zPrim.rotated(alpha, currentPoint);

            //             # Save the params
            //             curves.append(
            //                 (prev_point, first_cp, second_control_point, current_point))

            // Save the params
            curves.push([prevPoint, firstCp, secondControlPoint, currentPoint]);

            //             # Calculate the first control point for the second curve
            //             # (mirrors the second cp of the last curve)
            //             control_point_distance = self.cp_distance_for_segment(
            //                 current_point, next_point)
            //             if a == 0:
            //                 a = 0.0001
            //             k = control_point_distance / a
            //             q_prim = current_point + k * (next_point - current_point)
            //             first_cp = q_prim.rotated(-alpha, current_point)

            //             prev_point = current_point

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

        //         # If the head anchor type is AUTO - infer it
        //         if (state.has_head_anchor()
        //                 and state.head_anchor_type == ArrowAnchorType.AUTO):
        //             head_note = pamet.note(state.page_id, state.head_note_id)
        //             note_view = self.map_page_view.note_widget_by_note_gid(
        //                 head_note.gid())

        //             head_anchor_type = self.infer_arrow_anchor_type(
        //                 second_point, note_view.rect())
        //         else:
        //             head_anchor_type = state.head_anchor_type

        // If the head anchor type is AUTO - infer it
        let headAnchorType: ArrowAnchorType;
        if (this.hasHeadAnchor() && this.headAnchorType === ArrowAnchorType.AUTO) {
            headAnchorType = this.inferArrowAnchorType(secondPoint, this.headAnchorNoteViewState!.rect);
        } else {
            headAnchorType = this.headAnchorType;
        }

        //         if not state.mid_points:
        //             # Add the second control point for the last curve
        //             last_control_point = self.calculate_terminal_cp(
        //                 head_point, tail_point, control_point_distance,
        //                 head_anchor_type)
        //         else:
        //             # Add the second control point for the last curve
        //             last_control_point = self.calculate_terminal_cp(
        //                 head_point, current_point, control_point_distance,
        //                 head_anchor_type)

        // Add the second control point for the last curve
        let lastControlPoint: Point2D;
        if (!this.mid_points.length) {
            lastControlPoint = this.calculalteTerminalControlPoint(headPoint, tailPoint, controlPointDistance, headAnchorType);
        } else {
            lastControlPoint = this.calculalteTerminalControlPoint(headPoint, secondPoint, controlPointDistance, headAnchorType);
        }

        //         curves.append((prev_point, first_cp, last_control_point, head_point))

        //         return curves

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


    //     def edge_point_pos(self, edge_index: float) -> Point2D:
    //         """Returns the edge point position for the given index. Those
    //         include the tail, midpoints and head.

    //         The indeces are not integers, since the suggested new edge points
    //         are denoted with non-whole indices (e.g. 0.5, 1.5 etc.).
    //         More over the tail index is 0, and the head index is the last one.
    //         """

    //         if edge_index == 0:
    //             return self._cached_curves[0][0]
    //         elif edge_index % 1 == 0:
    //             curve_idx = int(edge_index - 1)
    //             curve = self._cached_curves[curve_idx]
    //             _, _, _, point = curve
    //             return copy(point)
    //         else:  # A non-whole index - a potential cp is requested
    //             curve_idx = int(edge_index)
    //             curve = self._cached_curves[curve_idx]
    //             p1, cp1, cp2, p2 = (QPointF(*p.as_tuple()) for p in curve)

    //             path = QPainterPath(p1)
    //             path.cubicTo(cp1, cp2, p2)
    //             potential_cp = path.pointAtPercent(0.5)
    //             return Point2D(potential_cp.x(), potential_cp.y())
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
    //     def edge_at(self, position: Point2D) -> Union[float, None]:
    //         real_pos = self.map_page_view.state().unproject_point(position)
    //         indices = self.state().all_edge_indices()
    //         for idx in indices:
    //             point = self.edge_point_pos(idx)

    //             if idx % 1 == 0:  # If it's a real edge
    //                 radius = ARROW_EDGE_RAIDUS
    //             else:
    //                 radius = POTENTIAL_EDGE_RADIUS
    //             if point.distance_to(real_pos) <= radius:
    //                 return idx
    //         return None

    edgeAt(position: Point2D): number | null {
        let realPos = position;
        let indices = this.allEdgeIndices();
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

    //     def intersects_circle(self, center: Point2D, radius: float) -> bool:
    //         if not self._cached_path:
    //             return False

    //         path = QPainterPath()
    //         path.addEllipse(QPointF(*center.as_tuple()), radius, radius)
    //         return self._cached_path.intersects(path)

    //     def intersects_rect(self, rect: Rectangle) -> bool:
    //         if not self._cached_path:
    //             return False

    //         selector_rect = QRectF(*rect.as_tuple())
    //         return self._cached_path.intersects(selector_rect)


}
