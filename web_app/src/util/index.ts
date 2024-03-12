import { PageChildViewState } from "../components/canvas/PageChildViewState";
import { getLogger } from "../fusion/logging";
import { Point2D } from "./Point2D";
import { Rectangle } from "./Rectangle";

export type ColorData = [number, number, number, number];
export type SelectionDict = Map<PageChildViewState, boolean>;

let log = getLogger('util/index.ts');

type TextAlignment = 'left' | 'center' | 'right';

export interface TextLayoutData {
    lines: string[];
    is_elided: boolean;
    alignment: TextAlignment;
}


export function color_to_css_rgba_string(color: ColorData) {
    // Convert from [0, 1] to [0, 255]. The alpha channel stays in [0, 1]!
    let r = Math.round(color[0] * 255)
    let g = Math.round(color[1] * 255)
    let b = Math.round(color[2] * 255)
    let color_string = `rgba(${r}, ${g}, ${b}, ${color[3]})`
    return color_string
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

let EMPTY_TOKEN = '';

class TextLayout {
    data: [string, Rectangle][] = [];
    is_elided: boolean = false;
    align: TextAlignment = 'center';

    text(): string {
        return this.data.join('\n');
    }
    toData(): TextLayoutData {
        return {
            lines: this.data.map((line) => line[0]),
            is_elided: this.is_elided,
            alignment: this.align,
        }
    }
}

// Init the canvas
let canvas: HTMLCanvasElement;
let canvasContext: CanvasRenderingContext2D;
let ELLIPSIS = '...';
let ellipsisWidth = 0;
let spaceWidth = 0;

const truncateText = (text: string, targetWidth: number, ctx: CanvasRenderingContext2D) => {
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

export function calculateTextLayout(text: string, textRect: Rectangle, font: string): TextLayoutData {
    // font: css font string

    if (!canvas || !canvasContext) {
        canvas = document.createElement('canvas');
        canvasContext = canvas.getContext('2d')!;
        if (!canvas || !canvasContext) {
            throw new Error('Failed to get canvas context');
        }
    }

    // Set the font
    canvasContext.font = font;

    ellipsisWidth = canvasContext.measureText(ELLIPSIS).width;
    spaceWidth = canvasContext.measureText(' ').width;

    // Get the needed parameters
    let lineSpacing = 20;

    // ?? Replace tabs with 4 spaces for consistent visualization (May not be the best place)
    text = text.replace('\t', '    ');

    // Get the y coordinates of the lines
    let lineVPositions: number[] = [];
    let line_y = textRect.top();
    while (line_y <= (textRect.bottom() - lineSpacing)) {
        lineVPositions.push(line_y);
        line_y += lineSpacing;
    }

    let textLayout = new TextLayout();

    // In case for some reason the text rect is too small to fit any text
    if (!lineVPositions.length && text) {
        textLayout.is_elided = true;
        return textLayout.toData();
    }

    // If there's a line break in the text: mark the alignment as left
    if (text.includes('\n')) {
        textLayout.align = 'left';
    }

    // Divide the text into words and "mark" the ones ending with an
    // EoL char (by keeping their indexes in eol_word_indices)
    let words: string[] = [];
    let eolWordIndices: number[] = [];
    for (let line of text.split('\n')) {
        // If the line is empty - push a special token
        // (and mark its index as an EoL word)
        let words_on_line: string[];

        if (!line) {
            words_on_line = [EMPTY_TOKEN]
        } else {
            words_on_line = line.split(' ');
        }
        words = words.concat(words_on_line);
        let lastWordIndex = words.length - 1;
        eolWordIndices.push(lastWordIndex);
    }

    // Start filling the available lines one by one
    let reachedWordIdx = 0;

    // For every available line: iterate through words until there's no
    // more space on the line
    for (let lineIdx = 0; lineIdx < lineVPositions.length; lineIdx++) {
        let lineY = lineVPositions[lineIdx];
        let wordsLeft = words.slice(reachedWordIdx);

        // If we've used all the words - there's nothing to do
        if (!wordsLeft) {
            break;
        }

        // Find the coordinates and dimentions of the line
        let lineRect = new Rectangle(textRect.left(), lineY, textRect.width(), lineSpacing);

        // Fill the line word by word
        let wordsOnLine: string[] = [];
        let widthLeft = textRect.width();
        let usedWords = 0;

        let truncateLine = false;
        let addEllipsis = false;

        for (let wordIdxOnLine = 0; wordIdxOnLine < wordsLeft.length; wordIdxOnLine++) {
            let atLastLine = lineIdx === (lineVPositions.length - 1);
            let atLastWord = wordIdxOnLine === (wordsLeft.length - 1);

            // Get the advance if we add the current word
            let advanceWithCurrentWord = canvasContext.measureText(wordsLeft[wordIdxOnLine]).width;
            if (wordIdxOnLine !== 0) { // Add the space width if not at the first word
                advanceWithCurrentWord += spaceWidth;
            }

            // If there's room for the next word - add it and continue
            // (if it's the last word - the loop will break afterwards)
            if (widthLeft >= advanceWithCurrentWord) {
                widthLeft -= advanceWithCurrentWord;
                wordsOnLine.push(wordsLeft[wordIdxOnLine]);
                usedWords += 1;

            } else {
                // If there's no room to add an elided word:
                // Elide only if we're at the last line or
                // if there's a single

                // // Add the word anyway
                // wordsOnLine.push(wordsLeft[wordIdxOnLine]);
                // usedWords += 1;
                // truncateLine = true;
                // addEllipsis = true;

                if (atLastLine) {
                    if (widthLeft < ellipsisWidth) { // There's no room for a partial/elided word
                        truncateLine = true;
                        addEllipsis = true;
                    } else { // There's room for a partial/elided word
                        wordsOnLine.push(wordsLeft[wordIdxOnLine]);
                        usedWords += 1;
                        truncateLine = true;
                        addEllipsis = true;
                    }
                } else if (wordIdxOnLine === 0) {
                    // If it's the first word on the line and it's just too long
                    // elide it
                    usedWords += 1;

                    wordsOnLine.push(wordsLeft[wordIdxOnLine]);
                    truncateLine = true;
                    addEllipsis = true;
                } // Else (there's no room for the word and we're not on the
                // last line) - we break (=word-wrap) and continue to the next line
                break;
            }

            // Check if we're on EoL (because of a line break in the text)
            if (eolWordIndices.includes(reachedWordIdx + wordIdxOnLine)) {
                if (atLastLine && !atLastWord) {
                    addEllipsis = true;
                }
                break; //should break anyway
            }
        }

        reachedWordIdx += usedWords;
        let lineText = wordsOnLine.join(' ');

        // // tmp log
        // if (truncateLine || addEllipsis) {
        //     log.info('trunc, addEllipsis', truncateLine, addEllipsis)
        //     log.info('line before truncate', lineText)
        // }

        if (truncateLine) {
            let width = textRect.width() - ellipsisWidth;
            lineText = truncateText(lineText, width, canvasContext);
        }

        // if (truncateLine || addEllipsis) { //tmp log
        //     log.info('line after truncate', lineText)
        // }

        if (addEllipsis) {
            textLayout.is_elided = true;
            lineText = lineText + ELLIPSIS;
        }

        // if (truncateLine || addEllipsis) { //tmp log
        //     log.info('line after ellipsis', lineText)
        // }


        textLayout.data.push([lineText, lineRect]);

        // Avoid adding empty lines at the end
        if (wordsLeft.length === 0) {
            if (wordsOnLine.length === 0) {
                textLayout.data.pop();
            }
            break;
        }

    }
    // // tmp debug
    // if (text.startsWith('Elide')) {
    //     log.info('textLayout', textLayout)
    //     log.info('rect', textRect)
    // }
    return textLayout.toData();
}


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
    let t, currentLength;
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
