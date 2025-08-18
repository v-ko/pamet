import { ImageConversionPreset } from "fusion/util/media";
import { HexColorData } from "fusion/primitives/Color";

// Base geometry
export const NO_SCALE_LINE_SPACING = 20

export const ALIGNMENT_GRID_UNIT = 10
export const AGU = ALIGNMENT_GRID_UNIT

export const PROPOSED_MAX_PAGE_WIDTH = 1000 * AGU;
export const PROPOSED_MAX_PAGE_HEIGHT = 1000 * AGU;

// Navigation
export const MIN_HEIGHT_SCALE = 0.2
export const MAX_HEIGHT_SCALE = 200

export const DEFAULT_EYE_HEIGHT = 40


// Note related
export const NOTE_MARGIN = AGU / 2
export const DEFAULT_NOTE_WIDTH = 32 * AGU
export const DEFAULT_NOTE_HEIGHT = 16 * AGU
export const MIN_NOTE_WIDTH = 3 * AGU
export const MIN_NOTE_HEIGHT = 3 * AGU
export const MAX_NOTE_WIDTH = 192 * AGU
export const MAX_NOTE_HEIGHT = 192 * AGU

export const RESIZE_CIRCLE_RADIUS = 2 * AGU
export const ALIGNMENT_LINE_LENGTH = 12 * AGU


export const DEFAULT_NOTE_FONT_SIZE = 18
export const DEFAULT_NOTE_FONT_FAMILY = 'Open Sans'
export const DEFAULT_NOTE_FONT_FAMILY_GENERIC = 'sans-serif'
export const PREFERRED_TEXT_NOTE_ASPECT_RATIO = 5

export const DEFAULT_FONT_STRING = `${DEFAULT_NOTE_FONT_SIZE}px/${NO_SCALE_LINE_SPACING}px ` +
    `'${DEFAULT_NOTE_FONT_FAMILY}', ` +
    `${DEFAULT_NOTE_FONT_FAMILY_GENERIC}`;

export const NOTE_BORDER_WIDTH = 0.5

// Arrow related
export const ARROW_SELECTION_RADIUS = 10

export const ARROW_CONTROL_POINT_RAIDUS = 25
export const DEFAULT_ARROW_THICKNESS = 1.5
export const ARROW_SELECTION_THICKNESS_DELTA = 3.5
export const CONTROL_POINT_RADIUS = 15
export const POTENTIAL_CONTROL_POINT_RADIUS = CONTROL_POINT_RADIUS * 0.7
export const ARROW_ANCHOR_ON_NOTE_SUGGEST_RADIUS = 2 * AGU
export const ARROW_CONTROL_POINT_RADIUS = 1.5 * AGU
export const ARROW_POTENTIAL_CONTROL_POINT_RADIUS = ARROW_CONTROL_POINT_RADIUS * 0.7

// Page render and cache related
export const MAX_RENDER_TIME = 0.025  // (in seconds) ~24 fps
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

// To consider:
// Command palette
// Panels
// Note edit view
// Canvas
// System modal dialog
// Future:
// Search and other utils pane
// Alert dialog?
export enum PametTabIndex {
    Page = 0,

    // Note Edit View tab indices
    NoteEditView_Tool1 = 10,
    NoteEditView_Tool2 = 11,
    NoteEditView_Tool3 = 12,
    NoteEditView_Tool4 = 13,

    NoteEditView_ImageDropZone = 14,
    NoteEditView_ImageUploadFile = 15,
    NoteEditView_ImageFromUrl = 16,
    NoteEditView_ImageCreateNew = 17,

    NoteEditView_LinkInput = 18,
    NoteEditView_InternalLinkRemoveButton = 19,
    NoteEditView_LinkGetTitleButton = 20,

    NoteEditViewText = 21,
    NoteEditViewSave = 22,
    NoteEditViewCancel = 23,
}

// Media related
export const MAX_MEDIA_NAME_LENGTH = 100;

// Media constraints
// See policies.ts for usage
export const MAX_IMAGE_SIZE = 5 * 1000 * 1000; // 5 MB
export const MAX_IMAGE_DIMENSION = 2560; // for either width or height
export const MAX_IMAGE_DIMENSION_FOR_COMPRESSION = 8192; // Reject larger images to avoid memory problems
export const MAX_FILE_UPLOAD_SIZE_BYTES = 40 * 1000 * 1000; // 40 MB


export const IMAGE_CONVERSION_PRESET_JPG: ImageConversionPreset = {
    maxWidth: 2560,
    maxHeight: 2560,
    mimeType: 'image/jpeg',
    quality: 0.9, // High quality
};

export const IMAGE_CONVERSION_PRESET_PNG: ImageConversionPreset = {
    maxWidth: 1920,
    maxHeight: 1920,
    mimeType: 'image/png',
    // PNG quality is about compression effort (0-9), not visual quality.
    // The canvas 'toBlob' for PNG doesn't support a quality/effort setting.
    // It's effectively lossless but without control over compression level.
};

