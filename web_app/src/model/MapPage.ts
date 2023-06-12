import { EntityData } from './Entity';

export interface TourSegment {
  link: string;
  html: string;
}

export interface MapPageData extends EntityData {
  name: string;
  created: string;
  modified: string;
  tour_segments: TourSegment[];
}
