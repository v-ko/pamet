import { HexColorData } from "../util/Color";

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

export const RESIZE_CIRCLE_RADIUS = 2 * AGU
export const ALIGNMENT_LINE_LENGTH = 12 * AGU
export const ARROW_ANCHOR_ON_NOTE_SUGGEST_RADIUS = 2 * AGU
export const ARROW_CONTROL_POINT_RADIUS = 1.5 * AGU
export const ARROW_POTENTIAL_CONTROL_POINT_RADIUS = ARROW_CONTROL_POINT_RADIUS * 0.7

export const DEFAULT_NOTE_FONT_SIZE = 18
export const DEFAULT_NOTE_FONT_FAMILY = 'Open Sans'
export const DEFAULT_NOTE_FONT_FAMILY_GENERIC = 'sans-serif'
export const DEFAULT_NOTE_LINE_HEIGHT = 20
export const PREFERRED_TEXT_NOTE_ASPECT_RATIO = 5

export const DEFAULT_FONT_STRING = `${DEFAULT_NOTE_FONT_SIZE}px/${DEFAULT_NOTE_LINE_HEIGHT}px ` +
    `'${DEFAULT_NOTE_FONT_FAMILY}', ` +
    `${DEFAULT_NOTE_FONT_FAMILY_GENERIC}`;

export const ARROW_SELECTION_RADIUS = 10

export const ARROW_CONTROL_POINT_RAIDUS = 25
export const DEFAULT_ARROW_THICKNESS = 1.5
export const ARROW_SELECTION_THICKNESS_DELTA = 3.5
export const CONTROL_POINT_RADIUS = 15
export const POTENTIAL_CONTROL_POINT_RADIUS = CONTROL_POINT_RADIUS * 0.7

// Page render and cache related
export const MAX_RENDER_TIME = 0.017  // (in seconds) ~60 fps
export const IMAGE_CACHE_PADDING = 3;

// Colors
export const DEFAULT_TEXT_COLOR_ROLE = 'onPrimary'
export const DEFAULT_BACKGROUND_COLOR_ROLE = 'primary'
export const SELECTED_ITEM_OVERLAY_COLOR_ROLE = 'itemSelectionOverlay'
export const DRAG_SELECT_COLOR_ROLE = 'interactiveSelectionMask'

// Hardcoded color roles. Will be made dynamic at some point.
// Naming: Use Material-like color roles  https://m3.material.io/styles/color/roles
export const COLOR_ROLE_MAP: { [key: string]: HexColorData } = {
    'primary': '#0000ff1a', // blue transparent background
    'onPrimary': '#0000ff', // blue text
    'error': '#ff00001a', // red transparent background
    'onError': '#ff0000', // red text
    'success': '#00ff001a', // green transparent background
    'onSuccess': '#00a33c', // green text
    'surface': '#ffffff', // white background
    'onSurface': '#000000', // black text
    'surfaceDim': '#0000001a', // black transparent background
    'itemSelectionOverlay': '#ffff0080',  // yellow transparent selection overlay
    'interactiveSelectionMask': '#64646433',  // grey transparent selection mask
    'transparent': '#00000000'  // transparent
}

export enum PametTabIndex {
    Page = 0,
    NoteEditViewWidget1 = 10,
    NoteEditViewWidget2 = 11,
    NoteEditViewWidget3 = 12,
    NoteEditViewWidget4 = 13,
    NoteEditViewWidget5 = 14,
    NoteEditViewWidget6 = 15,
    NoteEditViewWidget7 = 16,
    NoteEditViewWidget8 = 17,
    NoteEditViewWidget9 = 18,
    NoteEditViewWidget10 = 19,
    NoteEditViewWidget11 = 20,
}
