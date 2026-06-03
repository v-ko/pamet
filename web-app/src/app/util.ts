import { ElementViewState } from "@/views/page/ElementViewState";
import { ALIGNMENT_GRID_UNIT } from "@/app/constants";
import { getLogger } from "sivkit/logging";
import { Point2D, Vector2D } from "sivkit/primitives/Point2D";
import { Rectangle } from "sivkit/primitives/Rectangle";

// Clipboard item types
export type ClipboardItemType = 'text' | 'url' | 'image';

// Clipboard item interface
export interface ClipboardItem {
    type: ClipboardItemType;
    text?: string;
    url?: string;
    image_blob?: Blob;
    mime_type?: string;
}

/**
 * Parse clipboard data into a structured format
 */
export async function parseClipboardContents(): Promise<ClipboardItem[]> {
    const result: ClipboardItem[] = [];

    try {
        // Read clipboard items
        const clipboardItems = await navigator.clipboard.read();

        // Process each item
        for (const item of clipboardItems) {
            // Process images
            const imageTypes = item.types.filter(type => type.startsWith('image/'));
            for (const imageType of imageTypes) {
                try {
                    const blob = await item.getType(imageType);
                    result.push({
                        type: 'image',
                        image_blob: blob,
                        mime_type: imageType
                    });
                } catch (e) {
                    log.error('Error getting image from clipboard:', e);
                }
            }

            // Process text
            if (item.types.includes('text/plain') || item.types.includes('text/html')) {
                try {
                    const blob = await item.getType('text/plain');
                    const text = await blob.text();

                    // Split text by double newlines
                    const textParts = text.split(/\n\s*\n/);

                    // Process each part separately
                    for (const part of textParts) {
                        const trimmedPart = part.trim();
                        if (!trimmedPart) continue; // Skip empty parts

                        // Check if text is a URL
                        try {
                            const url = new URL(trimmedPart);
                            if (url.protocol === 'http:' || url.protocol === 'https:') {
                                // Add as URL item
                                result.push({
                                    type: 'url',
                                    text: trimmedPart,
                                    url: url.href
                                });
                            } else {
                                // Add as regular text
                                result.push({
                                    type: 'text',
                                    text: trimmedPart
                                });
                            }
                        } catch {
                            // Not a valid URL, add as regular text
                            result.push({
                                type: 'text',
                                text: trimmedPart
                            });
                        }
                    }
                } catch (e) {
                    log.error('Error getting text from clipboard:', e);
                }
            }
        }
    } catch (error) {
        log.error('Error parsing clipboard contents:', error);
    }

    return result;
}

export type SelectionDict = Map<ElementViewState, boolean>;

export let log = getLogger('primitives/index.ts');


export function snapToGrid(x: number): number {
    return Math.round(x / ALIGNMENT_GRID_UNIT) * ALIGNMENT_GRID_UNIT;
}

export function snapVectorToGrid<T extends Vector2D>(v: T): T {
    let newV = v.copy()
    newV.divide_inplace(ALIGNMENT_GRID_UNIT)
    newV.round_inplace()
    newV.multiply_inplace(ALIGNMENT_GRID_UNIT)
    return newV
}

export function snapVectorToGrid_inplace<T extends Vector2D>(v: T): T {
    v.divide_inplace(ALIGNMENT_GRID_UNIT)
    v.round_inplace()
    v.multiply_inplace(ALIGNMENT_GRID_UNIT)
    return v
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
        return this.lines.join('\n');
    }
    get lines(): string[] {
        return this._linesData.map((lineData) => lineData[0]);
    }
    get lineRects(): Rectangle[] {
        return this._linesData.map((lineData) => lineData[1]);
    }
}


export const truncateText = (text: string, targetWidth: number, ctx: OffscreenCanvasRenderingContext2D) => {
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

export function bezierPoint(t: number, P0: Point2D, P1: Point2D, P2: Point2D, P3: Point2D): Point2D {
    let p = new Point2D([0, 0]);
    return bezierPoint_inplace(t, P0, P1, P2, P3, p);
}

function bezierPoint_inplace(t: number, P0: Point2D, P1: Point2D, P2: Point2D, P3: Point2D, p_inplace: Point2D): Point2D {
    const u = 1 - t;
    const tt = t * t;
    const uu = u * u;
    const uuu = uu * u;
    const ttt = tt * t;

    p_inplace.x = uuu * P0.x; // first term
    p_inplace.y = uuu * P0.y;
    p_inplace.x += 3 * uu * t * P1.x; // second term
    p_inplace.y += 3 * uu * t * P1.y;
    p_inplace.x += 3 * u * tt * P2.x; // third term
    p_inplace.y += 3 * u * tt * P2.y;
    p_inplace.x += ttt * P3.x; // fourth term
    p_inplace.y += ttt * P3.y;
    return p_inplace;
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
        let currentPoint = new Point2D([0, 0]);
        for (let i = 1; i <= steps; i++) {
            let ct = i / numSegments;
            bezierPoint_inplace(ct, startPoint, cp1, cp2, endPoint, currentPoint);
            length += previousPoint.distanceTo(currentPoint);
            previousPoint = currentPoint.copy();
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

/** Solve at³ + bt² + ct + d = 0, return real roots in [0, 1].
 *  Used to find at what parameter values a cubic bezier curve crosses a given line.
 *  Uses the depressed cubic / trigonometric method for 3-root cases. */
function solveCubicInUnitInterval(a: number, b: number, c: number, d: number): number[] {
    const EPS = 1e-8;
    let roots: number[] = [];

    if (Math.abs(a) < EPS) {
        // Degenerate: quadratic bt² + ct + d = 0
        if (Math.abs(b) < EPS) {
            // Linear: ct + d = 0
            if (Math.abs(c) > EPS) roots.push(-d / c);
        } else {
            let disc = c * c - 4 * b * d;
            if (disc >= 0) {
                let sq = Math.sqrt(disc);
                roots.push((-c + sq) / (2 * b));
                roots.push((-c - sq) / (2 * b));
            }
        }
    } else {
        // Depressed cubic: u³ + pu + q = 0  via substitution t = u - b/(3a)
        let ba = b / a, ca = c / a, da = d / a;
        let p = (3 * ca - ba * ba) / 3;
        let q = (2 * ba * ba * ba - 9 * ba * ca + 27 * da) / 27;
        let disc = -(4 * p * p * p + 27 * q * q);

        if (disc > EPS) {
            // Three real roots — trigonometric method (avoids complex arithmetic)
            let mp3 = -p / 3;
            let r = 2 * Math.sqrt(mp3);
            let cosArg = (3 * q) / (2 * p) * Math.sqrt(-3 / p);
            cosArg = Math.max(-1, Math.min(1, cosArg)); // clamp for float safety
            let theta = Math.acos(cosArg) / 3;
            let shift = -ba / 3;
            roots.push(r * Math.cos(theta) + shift);
            roots.push(r * Math.cos(theta - 2 * Math.PI / 3) + shift);
            roots.push(r * Math.cos(theta + 2 * Math.PI / 3) + shift);
        } else {
            // One real root — Cardano's formula
            let halfQ = -q / 2;
            let inner = q * q / 4 + p * p * p / 27;
            if (inner < 0) inner = 0; // numerical guard
            let sqrtInner = Math.sqrt(inner);
            let u = Math.cbrt(halfQ + sqrtInner);
            let v = Math.cbrt(halfQ - sqrtInner);
            roots.push(u + v - ba / 3);
        }
    }

    // Filter to [0, 1] with small tolerance and clamp
    return roots.filter(t => t >= -EPS && t <= 1 + EPS)
                .map(t => Math.max(0, Math.min(1, t)));
}

/** Check if a cubic bezier curve intersects an axis-aligned rectangle.
 *  For each rect edge (4 axis-aligned lines), we solve the cubic polynomial
 *  analytically to find exact crossing points — no sampling needed. */
export function bezierIntersectsRect(
    P0: Point2D, P1: Point2D, P2: Point2D, P3: Point2D,
    rect: Rectangle
): boolean {
    // Expand the cubic bezier x(t) = ax*t³ + bx*t² + cx*t + dx
    let ax = -P0.x + 3 * P1.x - 3 * P2.x + P3.x;
    let bx = 3 * P0.x - 6 * P1.x + 3 * P2.x;
    let cx = -3 * P0.x + 3 * P1.x;
    let dx = P0.x;
    // Same for y(t)
    let ay = -P0.y + 3 * P1.y - 3 * P2.y + P3.y;
    let by = 3 * P0.y - 6 * P1.y + 3 * P2.y;
    let cy = -3 * P0.y + 3 * P1.y;
    let dy = P0.y;

    let left = rect.left(), right = rect.right();
    let top = rect.top(), bottom = rect.bottom();

    // Check vertical edges (x = left, x = right):
    // solve ax*t³ + bx*t² + cx*t + (dx - edgeX) = 0, then check y in range
    for (let edgeX of [left, right]) {
        let roots = solveCubicInUnitInterval(ax, bx, cx, dx - edgeX);
        for (let t of roots) {
            let y = ((ay * t + by) * t + cy) * t + dy;
            if (y >= top && y <= bottom) return true;
        }
    }

    // Check horizontal edges (y = top, y = bottom):
    // solve ay*t³ + by*t² + cy*t + (dy - edgeY) = 0, then check x in range
    for (let edgeY of [top, bottom]) {
        let roots = solveCubicInUnitInterval(ay, by, cy, dy - edgeY);
        for (let t of roots) {
            let x = ((ax * t + bx) * t + cx) * t + dx;
            if (x >= left && x <= right) return true;
        }
    }

    return false;
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



export function buildDeviceBranchName(userId: string, deviceId: string): string {
    return `${userId}__${deviceId}`;
}

