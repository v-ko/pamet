import { Color } from '../util';
import { PointData } from '../util/Point2D';
import { EntityData } from './Entity';

export type BezierCurve = [PointData, PointData, PointData, PointData]

export interface ArrowCache {
  curves: BezierCurve[];
}

export interface ArrowData extends EntityData {
  tail_coords: PointData;
  head_coords: PointData;
  mid_point_coords: PointData[];
  head_note_id: string;
  tail_note_id: string;
  head_anchor: string;
  tail_anchor: string;
  color: Color;
  line_type: string;
  line_thickness: number;
  line_function_name: string;
  head_shape: string;
  tail_shape: string;
  cache: ArrowCache;
}
