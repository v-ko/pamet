import { entityType } from 'fusion/libs/Entity';
import { ColorData } from '../util';
import { Point2D, PointData } from '../util/Point2D';
import { PametElement, PametElementData } from './Element';


export enum ArrowAnchorType {
    none,
    auto,
    mid_left,
    top_mid,
    mid_right,
    bottom_mid,
}

export interface ArrowData extends PametElementData {
    tail_coords: PointData | null;
    head_coords: PointData | null;
    mid_point_coords: PointData[];
    head_note_id: string | null;
    tail_note_id: string | null;
    head_anchor: ArrowAnchorType;
    tail_anchor: ArrowAnchorType;
    color: ColorData;
    line_type: string;
    line_thickness: number;
    line_function_name: string;
    head_shape: string;
    tail_shape: string;
}

// Use camelCase for property names
@entityType('Arrow')
export class Arrow extends PametElement<ArrowData> implements ArrowData {
    get tail_coords(): PointData | null {
        return this._data.tail_coords;
    }
    get head_coords(): PointData | null {
        return this._data.head_coords;
    }
    get mid_point_coords(): PointData[] {
        return this._data.mid_point_coords;
    }
    get head_note_id(): string | null {
        return this._data.head_note_id;
    }
    set head_note_id(new_id: string | null) {
        this._data.head_note_id = new_id;
    }
    get tail_note_id(): string | null {
        return this._data.tail_note_id;
    }
    set tail_note_id(new_id: string | null) {
        this._data.tail_note_id = new_id;
    }
    get head_anchor(): ArrowAnchorType {
        return this._data.head_anchor;
    }
    get tail_anchor(): ArrowAnchorType {
        return this._data.tail_anchor;
    }
    get color(): ColorData {
        return this._data.color;
    }
    get line_type(): string {
        return this._data.line_type;
    }
    get line_thickness(): number {
        return this._data.line_thickness;
    }
    get line_function_name(): string {
        return this._data.line_function_name;
    }
    get head_shape(): string {
        return this._data.head_shape;
    }
    get tail_shape(): string {
        return this._data.tail_shape;
    }

    get tail_point(): Point2D | null {
        if (!this.tail_coords) {
            return null;
        }
        return Point2D.fromData(this.tail_coords);
    }

    set tail_point(point: Point2D | null) {
        if (point) {
            this._data.tail_coords = point.data();
        } else {
            this._data.tail_coords = null;
        }
    }

    get head_point(): Point2D | null {
        if (!this.head_coords) {
            return null;
        }
        return Point2D.fromData(this.head_coords);
    }

    set head_point(point: Point2D | null) {
        if (point) {
            this._data.head_coords = point.data();
        } else {
            this._data.head_coords = null;
        }
    }
    get mid_points(): Point2D[] {
        return this.mid_point_coords.map((mid_point) => Point2D.fromData(mid_point));
    }
    get_midpoint(idx: number): Point2D {
        return Point2D.fromData(this.mid_point_coords[idx]);
    }
    replace_midpoints(midpoint_list: Point2D[]) {
        this._data.mid_point_coords = midpoint_list.map((mp) => mp.data());
    }
    // get_color(): Color {
    //   return Color.fromData(this.color);
    // }
    // set_color(color: Color) {
    //   this._data.color = color.asData();
    // }
    get tailAnchorType(): ArrowAnchorType {
        return this.tail_anchor;
    }

    set tailAnchorType(new_type: ArrowAnchorType) {
        this._data.tail_anchor = new_type;
    }
    get headAnchorType(): ArrowAnchorType {
        return this.head_anchor;
    }
    set headAnchorType(new_type: ArrowAnchorType) {
        this._data.head_anchor = new_type;
    }
    hasTailAnchor(): boolean {
        return !!this.tail_note_id;
    }
    hasHeadAnchor(): boolean {
        return !!this.head_note_id;
    }
    // def edge_indices(self):
    //     mid_edge_count = 2 + len(self.mid_points)
    //     return list(range(mid_edge_count))
    edge_indices(): number[] {
        let mid_edge_count = 2 + this.mid_points.length;
        return Array.from(Array(mid_edge_count).keys());
    }
    // def potential_edge_indices(self):
    //     return [i + 0.5 for i in self.edge_indices()[:-1]]
    potential_edge_indices(): number[] {
        return this.edge_indices().map((i) => i + 0.5).slice(0, -1);
    }
    // def all_edge_indices(self):
    //     return sorted(self.edge_indices() + self.potential_edge_indices())
    allEdgeIndices(): number[] {
        return this.edge_indices().concat(this.potential_edge_indices()).sort();
    }
    // def set_tail(self,
    //              fixed_pos: Point2D = None,
    //              anchor_note_id: str = None,
    //              anchor_type: ArrowAnchorType = ArrowAnchorType.NONE):
    //     if fixed_pos and anchor_note_id:
    //         # The fixed pos is almost always propagated
    //         # but if there's an anchor note - it takes precedence
    //         fixed_pos = None

    //     if fixed_pos and anchor_type != ArrowAnchorType.NONE:
    //         raise Exception

    //     self.tail_point = fixed_pos
    //     self.tail_note_id = anchor_note_id
    //     self.tail_anchor_type = anchor_type
    setTail(fixed_pos: Point2D | null, anchor_note_id: string | null, anchor_type: ArrowAnchorType) {
        if (fixed_pos && anchor_note_id) {
            // The fixed pos is almost always propagated
            // but if there's an anchor note - it takes precedence
            fixed_pos = null;
        }

        if (fixed_pos && anchor_type != ArrowAnchorType.none) {
            throw new Error('fixed_pos and anchor_type != ArrowAnchorType.NONE');
        }

        this.tail_point = fixed_pos;
        this.tail_note_id = anchor_note_id;
        this.tailAnchorType = anchor_type;
    }
    // def set_head(self,
    //              fixed_pos: Point2D = None,
    //              anchor_note_id: str = None,
    //              anchor_type: ArrowAnchorType = ArrowAnchorType.NONE):
    //     if fixed_pos and anchor_note_id:
    //         # The fixed pos is almost always propagated
    //         # but if there's an anchor note - it takes precedence
    //         fixed_pos = None

    //     if fixed_pos and anchor_type != ArrowAnchorType.NONE:
    //         raise Exception

    //     self.head_point = fixed_pos
    //     self.head_note_id = anchor_note_id
    //     self.head_anchor_type = anchor_type
    setHead(fixed_pos: Point2D | null, anchor_note_id: string | null, anchor_type: ArrowAnchorType) {
        if (fixed_pos && anchor_note_id) {
            // The fixed pos is almost always propagated
            // but if there's an anchor note - it takes precedence
            fixed_pos = null;
        }

        if (fixed_pos && anchor_type != ArrowAnchorType.none) {
            throw new Error('fixed_pos and anchor_type != ArrowAnchorType.NONE');
        }

        this.head_point = fixed_pos;
        this.head_note_id = anchor_note_id;
        this.headAnchorType = anchor_type;
    }
}
