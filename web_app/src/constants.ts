import { ColorData } from "./util";

export const DEFAULT_TEXT_COLOR: ColorData = [0, 0, 1, 1];
export const DEFAULT_BACKGROUND_COLOR: ColorData = [0, 0, 1, 0.1];
export const SELECTION_OVERLAY_COLOR: ColorData = [1, 1, 0, 0.5];
export const DRAG_SELECT_COLOR: ColorData = [0.39, 0.39, 0.39, 0.2];

export const MIN_HEIGHT_SCALE = 0.2
export const MAX_HEIGHT_SCALE = 200

export const DEFAULT_EYE_HEIGHT = 40

export const NO_SCALE_LINE_SPACING = 20

export const ALIGNMENT_GRID_UNIT = 10
export const AGU = ALIGNMENT_GRID_UNIT

export const NOTE_MARGIN = AGU / 2
export const DEFAULT_NOTE_WIDTH = 32 * AGU
export const DEFAULT_NOTE_HEIGHT = 16 * AGU
export const MIN_NOTE_WIDTH = 3 * AGU
export const MIN_NOTE_HEIGHT = 3 * AGU
export const MAX_NOTE_WIDTH = 192 * AGU
export const MAX_NOTE_HEIGHT = 192 * AGU

export const DEFAULT_NOTE_FONT_SIZE = 18
export const DEFAULT_NOTE_FONT_FAMILY = 'Open Sans'
export const DEFAULT_NOTE_FONT_FAMILY_GENERIC = 'sans-serif'
export const DEFAULT_NOTE_LINE_HEIGHT = 20

export const ARROW_SELECTION_RADIUS = 10

export const ARROW_EDGE_RAIDUS = 25
export const DEFAULT_ARROW_THICKNESS = 1.5
export const ARROW_SELECTION_THICKNESS_DELTA = 3.5
export const CONTROL_POINT_RADIUS = 15
export const POTENTIAL_EDGE_RADIUS = CONTROL_POINT_RADIUS * 0.7

// Page render and cache related
export const MAX_RENDER_TIME = 0.017  // (in seconds) ~60 fps
export const IMAGE_CACHE_PADDING = 3
