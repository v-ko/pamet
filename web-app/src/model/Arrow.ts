import { entityType } from 'fusion/libs/Entity';
import { Point2D, PointData } from 'fusion/primitives/Point2D';
import { PametElement, PametElementData } from './Element';
import { Note } from './Note';


export type ArrowLineType = 'solid';  // To be extended
export type ArrowFunctionName = 'bezier_cubic';
export type ArrowHeadShape = 'arrow';

export enum ArrowAnchorOnNoteType {
    none,
    auto,
    mid_left,
    top_mid,
    mid_right,
    bottom_mid,
}

// Map enum values to strings
export const ArrowAnchorTypeToString: { [key in ArrowAnchorOnNoteType]: string } = {
    [ArrowAnchorOnNoteType.none]: 'none',
    [ArrowAnchorOnNoteType.auto]: 'auto',
    [ArrowAnchorOnNoteType.mid_left]: 'mid_left',
    [ArrowAnchorOnNoteType.top_mid]: 'top_mid',
    [ArrowAnchorOnNoteType.mid_right]: 'mid_right',
    [ArrowAnchorOnNoteType.bottom_mid]: 'bottom_mid',
};

// Map strings to enum values
export const StringToArrowAnchorType: { [key: string]: ArrowAnchorOnNoteType } = {
    'none': ArrowAnchorOnNoteType.none,
    'auto': ArrowAnchorOnNoteType.auto,
    'mid_left': ArrowAnchorOnNoteType.mid_left,
    'top_mid': ArrowAnchorOnNoteType.top_mid,
    'mid_right': ArrowAnchorOnNoteType.mid_right,
    'bottom_mid': ArrowAnchorOnNoteType.bottom_mid,
};

// export interface ArrowData extends PametElementData {
//     tail_coords: PointData | null;
//     head_coords: PointData | null;
//     mid_point_coords: PointData[];
//     head_note_id: string | null;
//     tail_note_id: string | null;
//     head_anchor: ArrowAnchorType;
//     tail_anchor: ArrowAnchorType;
//     color_role: string;
//     line_type: ArrowLineType;
//     line_thickness: number;
//     line_function_name: ArrowFunctionName;
//     head_shape: ArrowHeadShape;
//     tail_shape: ArrowHeadShape;
// }
export interface EndPointProps {
    position: PointData | null;
    noteAnchorId: string | null;
    noteAnchorType: string;
}

export interface ArrowStyle {
    color_role: string;
    line_type: ArrowLineType;
    thickness: number;
    line_function: ArrowFunctionName;
    head_shape: ArrowHeadShape;
    tail_shape: ArrowHeadShape;
}
export interface ArrowData extends PametElementData {
    tail: EndPointProps;
    head: EndPointProps;
    mid_points: PointData[];
    style: ArrowStyle;
}

// Use camelCase for property names
@entityType('Arrow')
export class Arrow extends PametElement<ArrowData> {
    get headNoteId(): string | null {
        return this._data.head.noteAnchorId;
    }

    get tailNoteId(): string | null {
        return this._data.tail.noteAnchorId;
    }

    get colorRole(): string {
        return this._data.style.color_role;
    }
    set colorRole(new_role: string) {
        this._data.style.color_role = new_role;
    }

    get lineType(): ArrowLineType {
        return this._data.style.line_type;
    }
    get thickness(): number {
        return this._data.style.thickness;
    }
    get lineFunctionName(): ArrowFunctionName {
        return this._data.style.line_function;
    }
    get headShape(): ArrowHeadShape {
        return this._data.style.head_shape;
    }
    get tailShape(): ArrowHeadShape {
        return this._data.style.tail_shape;
    }

    get tailPoint(): Point2D | null {
        if (!this._data.tail.position) {
            return null;
        }
        return Point2D.fromData(this._data.tail.position);
    }
    set tailPoint(point: Point2D | null) {
        if (point) {
            this._data.tail.position = point.data();
        } else {
            this._data.tail.position = null;
        }
    }

    get headPoint(): Point2D | null {
        if (!this._data.head.position) {
            return null;
        }
        return Point2D.fromData(this._data.head.position);
    }
    set headPoint(point: Point2D | null) {
        if (point) {
            this._data.head.position = point.data();
        } else {
            this._data.head.position = null;
        }
    }

    get midPoints(): Point2D[] {
        return this._data.mid_points.map((mid_point) => Point2D.fromData(mid_point));
    }
    getMidPoint(idx: number): Point2D {
        return Point2D.fromData(this._data.mid_points[idx]);
    }
    replaceMidpoints(midpoint_list: Point2D[]) {
        this._data.mid_points = midpoint_list.map((mp) => mp.data());
    }

    get tailAnchorType(): ArrowAnchorOnNoteType {
        return StringToArrowAnchorType[this._data.tail.noteAnchorType];
    }

    set tailAnchorType(new_type: ArrowAnchorOnNoteType) {
        this._data.tail.noteAnchorType = ArrowAnchorTypeToString[new_type];
    }

    get headAnchorType(): ArrowAnchorOnNoteType {
        return StringToArrowAnchorType[this._data.head.noteAnchorType];
    }
    set headAnchorType(new_type: ArrowAnchorOnNoteType) {
        this._data.head.noteAnchorType = ArrowAnchorTypeToString[new_type];
    }

    get tailAnchoredOnNote(): boolean {
        return !!this.tailNoteId;
    }
    get headAnchoredOnNote(): boolean {
        return !!this.headNoteId;
    }
    get tailPositionIsAbsolute(): boolean {
        return !!this._data.tail.position;
    }
    get headPositionIsAbsolute(): boolean {
        return !!this._data.head.position;
    }
    controlPointIndices(): number[] {
        let midPointCount = 2 + this.midPoints.length;
        return Array.from(Array(midPointCount).keys());
    }
    potentialControlPointIndices(): number[] {
        return this.controlPointIndices().map((i) => i + 0.5).slice(0, -1);
    }
    allControlPointIndices(): number[] {
        return this.controlPointIndices().concat(this.potentialControlPointIndices()).sort();
    }
    setTail(fixed_pos: Point2D | null, anchorNote: Note | null, anchor_type: ArrowAnchorOnNoteType) {
        if ((fixed_pos && anchorNote) || (!fixed_pos && !anchorNote)) {
            throw new Error('Exactly one of fixed_pos or anchorNote should be set');
        }

        if (fixed_pos && anchor_type != ArrowAnchorOnNoteType.none) {
            throw new Error('fixed_pos and anchor_type != ArrowAnchorType.NONE');
        }

        this.tailPoint = fixed_pos;
        this._data.tail.noteAnchorId = anchorNote ? anchorNote.own_id : null;
        this.tailAnchorType = anchor_type;
    }
    setHead(fixed_pos: Point2D | null, anchorNote: Note | null, anchor_type: ArrowAnchorOnNoteType) {
        if ((fixed_pos && anchorNote) || (!fixed_pos && !anchorNote)) {
            throw new Error('Exactly one of fixed_pos or anchorNote should be set');
        }

        if (fixed_pos && anchor_type != ArrowAnchorOnNoteType.none) {
            throw new Error('fixed_pos and anchor_type != ArrowAnchorType.NONE');
        }

        this.headPoint = fixed_pos;
        this._data.head.noteAnchorId = anchorNote ? anchorNote.own_id : null;
        this.headAnchorType = anchor_type;
    }
}

export function arrowAnchorPosition(note: Note, anchorType: ArrowAnchorOnNoteType): Point2D {
    const rect = note.rect();
    switch (anchorType) {
        case ArrowAnchorOnNoteType.mid_left:
            return rect.topLeft().add(new Point2D([0, rect.height() / 2]));
        case ArrowAnchorOnNoteType.top_mid:
            return rect.topLeft().add(new Point2D([rect.width() / 2, 0]));
        case ArrowAnchorOnNoteType.mid_right:
            return rect.topRight().add(new Point2D([0, rect.height() / 2]));
        case ArrowAnchorOnNoteType.bottom_mid:
            return rect.bottomLeft().add(new Point2D([rect.width() / 2, 0]));
        default:
            throw new Error('Invalid anchor type' + anchorType);
    }
}

export function anchorIntersectsCircle(note: Note, point: Point2D, radius: number): ArrowAnchorOnNoteType {
    for (const anchorType of [ArrowAnchorOnNoteType.mid_left, ArrowAnchorOnNoteType.top_mid, ArrowAnchorOnNoteType.mid_right, ArrowAnchorOnNoteType.bottom_mid]) {
        if (point.distanceTo(arrowAnchorPosition(note, anchorType)) < radius) {
            return anchorType;
        }
    }
    return ArrowAnchorOnNoteType.none;
}
