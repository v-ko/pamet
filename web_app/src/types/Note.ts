import { Color } from "./util";
import { EntityData } from "./Entity";

export interface NoteContent {
  text: string;
  url: string;
  image_url: string;
}
export interface NoteStyle {
  color: Color;
  background_color: Color;
}
export interface TextLayoutData {
  lines: string[];
  is_elided: boolean;
  alignment: string;
}
export interface NoteCache {
  text_layout_data: TextLayoutData;
}
export interface NoteMetadata {
}
export interface NoteData extends EntityData {
  own_id: string;
  page_id: string;
  content: NoteContent;
  geometry: [number, number, number, number];
  style: NoteStyle;
  created: string;
  modified: string;
  metadata: NoteMetadata;
  tags: string[];
  cache: NoteCache;  // Should be temporary
}
