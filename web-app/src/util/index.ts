import { ElementViewState } from "../components/page/ElementViewState";
import { ALIGNMENT_GRID_UNIT } from "../core/constants";
import { getLogger } from "fusion/logging";
import { Point2D, Vector2D } from "./Point2D";
import { Rectangle } from "./Rectangle";

export type SelectionDict = Map<ElementViewState, boolean>;

let log = getLogger('util/index.ts');


export function snapToGrid(x: number): number {
    return Math.round(x / ALIGNMENT_GRID_UNIT) * ALIGNMENT_GRID_UNIT;
}

export function snapVectorToGrid<T extends Vector2D>(v: T): T {
    return v.divide(ALIGNMENT_GRID_UNIT).round().multiply(ALIGNMENT_GRID_UNIT);
}

export interface PametUrlProps {
    page_id?: string,
    viewportCenter?: Point2D,
    viewportHeight?: number,
    // selection?: Array<string>,
    focused_note_id?: string,
}

export function parsePametUrl(url_string: string): PametUrlProps {
    let url = new URL(url_string);

    // The page_id is a part of the path like /p/page_id/
    // So if there's no /p/ it will remain unset
    let page_id: string | undefined = undefined;
    if (url.pathname.startsWith("/p/")) {
        page_id = url.pathname.split("/")[2];
    }

    // The anchor is a key/value pair for either eye_at= (map position)
    // or note= for a note id

    // The eye_at is in the fragment/anchor and is in the form height/x/y
    let viewportCenter: Point2D | undefined = undefined;
    let viewportHeight: number | undefined = undefined;
    let focused_note_id: string | undefined = undefined;

    let eye_at = url.hash.split("#eye_at=")[1];
    if (eye_at) {
        let [height, x, y] = eye_at.split("/").map(parseFloat);
        if (!(isNaN(height) || isNaN(x) || isNaN(y))) {
            viewportCenter = new Point2D(x, y);
            viewportHeight = height;
        }
    }

    // Get the focused note from the anchor
    focused_note_id = url.hash.split("#note=")[1];

    return {
        page_id: page_id,
        viewportCenter: viewportCenter,
        viewportHeight: viewportHeight,
        focused_note_id: focused_note_id,
    }
}

export let EMPTY_TOKEN = '';

type TextAlignment = 'left' | 'center' | 'right';

export class TextLayout {
    textRect: Rectangle;
    _linesData: [string, Rectangle][] = [];
    isElided: boolean = false;
    alignment: TextAlignment = 'center';

    constructor(textRect: Rectangle) {
        this.textRect = textRect;
    }

    text(): string {
        return this._linesData.join('\n');
    }
    get lines(): string[] {
        return this._linesData.map((lineData) => lineData[0]);
    }
    get lineRects(): Rectangle[] {
        return this._linesData.map((lineData) => lineData[1]);
    }
}


export const truncateText = (text: string, targetWidth: number, ctx: CanvasRenderingContext2D) => {
    if (targetWidth <= 0) {
        return '';
    }

    let left = 0;
    let right = text.length;
    let mid: number;
    let textPart: string;
    let textPartWidth: number;

    while (left <= right) {
        mid = Math.floor((left + right) / 2);
        textPart = text.slice(0, mid);
        textPartWidth = ctx.measureText(textPart).width;

        if (textPartWidth <= targetWidth) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }

    // The right pointer will be at the largest length that fits
    // So we return the word part that corresponds to this length
    return text.slice(0, right);
};

function bezierPoint(t: number, P0: Point2D, P1: Point2D, P2: Point2D, P3: Point2D): Point2D {
    const u = 1 - t;
    const tt = t * t;
    const uu = u * u;
    const uuu = uu * u;
    const ttt = tt * t;

    let p = new Point2D();
    p.x = uuu * P0.x; // first term
    p.y = uuu * P0.y;
    p.x += 3 * uu * t * P1.x; // second term
    p.y += 3 * uu * t * P1.y;
    p.x += 3 * u * tt * P2.x; // third term
    p.y += 3 * u * tt * P2.y;
    p.x += ttt * P3.x; // fourth term
    p.y += ttt * P3.y;
    return p;
}

export function approximateMidpointOfBezierCurve(startPoint: Point2D, cp1: Point2D, cp2: Point2D, endPoint: Point2D, precision_k: number = 1): Point2D {
    // Approximate the number of segments based on the distance between start/end/control points
    let pathLength = startPoint.distanceTo(cp1) + cp1.distanceTo(cp2) + cp2.distanceTo(endPoint);
    let numSegments = Math.ceil(pathLength / (1 / precision_k)); // Adjust the divisor to balance performance and accuracy

    // Function to calculate the length of Bezier curve up to a certain point
    function calculateLengthUpToPoint(t: number): number {
        let length = 0;
        let previousPoint = startPoint;
        let steps = Math.ceil(t * numSegments);
        for (let i = 1; i <= steps; i++) {
            let ct = i / numSegments;
            let currentPoint = bezierPoint(ct, startPoint, cp1, cp2, endPoint);
            length += previousPoint.distanceTo(currentPoint);
            previousPoint = currentPoint;
        }
        return length;
    }

    // Calculate total length
    let totalLength = calculateLengthUpToPoint(1);

    // Binary search to find the midpoint
    let lower = 0;
    let upper = 1;
    let t = 0, currentLength;
    while (upper - lower > 1e-5) { // Adjust the epsilon for precision
        t = (lower + upper) / 2;
        currentLength = calculateLengthUpToPoint(t);
        if (currentLength < totalLength / 2) {
            lower = t;
        } else {
            upper = t;
        }
    }

    return bezierPoint(t, startPoint, cp1, cp2, endPoint);
}
export function drawCrossingDiagonals(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    spacing: number
) {
    ctx.save();
    ctx.lineWidth = 1;

    const diagonalCount = Math.ceil((width + height) / spacing);

    for (let i = 0; i <= diagonalCount; i++) {
        let offset = i * spacing;

        // Calculate start and end points for lines from bottom-left to top-right (\)
        let startX_BLtoTR = x + (offset < height ? 0 : offset - height);
        let startY_BLtoTR = y + (offset < height ? height - offset : 0);
        let endX_BLtoTR = x + (offset < width ? offset : width);
        let endY_BLtoTR = y + (offset < width ? height : height - (offset - width));

        // Calculate start and end points for lines from top-left to bottom-right (/)
        let startX_TLtoBR = x + (offset < height ? 0 : offset - height);
        let startY_TLtoBR = y + (offset < height ? offset : height);
        let endX_TLtoBR = x + (offset < width ? offset : width);
        let endY_TLtoBR = y + (offset < width ? 0 : offset - width);

        // Draw lines from bottom-left to top-right (\)
        ctx.beginPath();
        ctx.moveTo(startX_BLtoTR, startY_BLtoTR);
        ctx.lineTo(endX_BLtoTR, endY_BLtoTR);
        ctx.stroke();
        ctx.closePath();

        // Draw lines from top-left to bottom-right (/)
        ctx.beginPath();
        ctx.moveTo(startX_TLtoBR, startY_TLtoBR);
        ctx.lineTo(endX_TLtoBR, endY_TLtoBR);
        ctx.stroke();
        ctx.closePath();
    }

    ctx.restore();
}
