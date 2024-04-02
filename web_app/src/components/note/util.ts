import { ALIGNMENT_GRID_UNIT, DEFAULT_FONT_STRING, DEFAULT_NOTE_HEIGHT, DEFAULT_NOTE_WIDTH, MAX_NOTE_WIDTH, MIN_NOTE_HEIGHT, MIN_NOTE_WIDTH, NOTE_MARGIN, PREFERRED_TEXT_NOTE_ASPECT_RATIO } from "../../constants";
import { Note } from "../../model/Note";
import { ImageNote } from "../../model/ImageNote";
import { Rectangle } from "../../util/Rectangle";
import { Size } from "../../util/Size";
import { TextLayout, EMPTY_TOKEN, truncateText } from "../../util";

export function textRect(forArea: Rectangle): Rectangle {
    return new Rectangle(
        forArea.x + NOTE_MARGIN,
        forArea.y + NOTE_MARGIN,
        forArea.w - 2 * NOTE_MARGIN,
        forArea.h - 2 * NOTE_MARGIN);
}


export function imageRect(forArea: Rectangle, imageSize: Size): Rectangle {
    /**
     * Returns a centered rectangle, keeping the image aspect ratio
     */
    let size = forArea.size();
    let imageAR = imageSize.x / imageSize.y;
    let areaAR = size.x / size.y;
    let imageRect: Rectangle;

    if (imageAR > areaAR) {
        let w = size.x;
        let h = w / imageAR;
        imageRect = new Rectangle(forArea.x, forArea.y + (size.y - h) / 2, w, h);
    } else if (imageAR < areaAR) {
        let h = size.y;
        let w = h * imageAR;
        imageRect = new Rectangle(forArea.x + (size.x - w) / 2, forArea.y, w, h);
    } else {
        imageRect = new Rectangle(forArea.x, forArea.y, forArea.w, forArea.h);
    }
    return imageRect;
}

// Init the canvas
export let canvas: HTMLCanvasElement;
export let canvasContext: CanvasRenderingContext2D;
export let ELLIPSIS = '...';
export let ellipsisWidth = 0;
export let spaceWidth = 0;


export function calculateTextLayout(text: string, textRect: Rectangle, font: string): TextLayout {
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

    let textLayout = new TextLayout(textRect);

    // In case for some reason the text rect is too small to fit any text
    if (!lineVPositions.length && text) {
        textLayout.isElided = true;
        return textLayout;
    }

    // If there's a line break in the text: mark the alignment as left
    if (text.includes('\n')) {
        textLayout.alignment = 'left';
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
            words_on_line = [EMPTY_TOKEN];
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
        let lineRect = new Rectangle(textRect.left(), lineY, textRect.width, lineSpacing);

        // Fill the line word by word
        let wordsOnLine: string[] = [];
        let widthLeft = textRect.width;
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
            let width = textRect.width - ellipsisWidth;
            lineText = truncateText(lineText, width, canvasContext);
        }

        // if (truncateLine || addEllipsis) { //tmp log
        //     log.info('line after truncate', lineText)
        // }
        if (addEllipsis) {
            textLayout.isElided = true;
            lineText = lineText + ELLIPSIS;
        }

        // if (truncateLine || addEllipsis) { //tmp log
        //     log.info('line after ellipsis', lineText)
        // }
        textLayout._linesData.push([lineText, lineRect]);

        // Avoid adding empty lines at the end
        if (wordsLeft.length === 0) {
            if (wordsOnLine.length === 0) {
                textLayout._linesData.pop();
            }
            break;
        }

    }
    // // tmp debug
    // if (text.startsWith('Elide')) {
    //     log.info('textLayout', textLayout)
    //     log.info('rect', textRect)
    // }
    return textLayout;
}

export function minimalNonelidedSize(note: Note): Size {
    /** Do a binary search to get the minimal note size */
    let defaultNoteSize = new Size(DEFAULT_NOTE_WIDTH, DEFAULT_NOTE_HEIGHT);
    let noteFont = DEFAULT_FONT_STRING

    // If it's an image note - fit to the image (if no image - default size)
    if (note instanceof ImageNote) {
        let imageNote = note as ImageNote;
        try {
            return imageNote.imageRect().size();
        } catch (e) {
            return defaultNoteSize;
        }
    }

    let text = note.text;

    if (!text) {
        return defaultNoteSize;
    }

    // Start with the largest possible rect
    let testRect = note.rect();
    let maxW = MAX_NOTE_WIDTH;

    let unit = ALIGNMENT_GRID_UNIT;
    let minWidthU = Math.floor(DEFAULT_NOTE_WIDTH / unit);

    // Do a binary search for the proper width (keeping the aspect ratio)
    let lowWidthBound = 0;
    let highWidthBound = Math.round(maxW / unit - minWidthU);
    while ((highWidthBound - lowWidthBound) > 0) {
        let testWidthIt = Math.floor((highWidthBound + lowWidthBound) / 2);
        let testWidthU = minWidthU + testWidthIt;
        let testHeightU = Math.round(testWidthU / PREFERRED_TEXT_NOTE_ASPECT_RATIO);

        let textSize = new Size(testWidthU * unit, testHeightU * unit);
        testRect.setSize(textSize);
        note.setRect(testRect);
        let textLayout = calculateTextLayout(text, note.textRect(), noteFont);
        if (textLayout.isElided) {
            lowWidthBound = testWidthIt + 1;
        } else {
            highWidthBound = testWidthIt;
        }
    }

    // Fine adjust the size by reducing it one unit per step and
    // stopping upon text elide
    let widthU = minWidthU + lowWidthBound;
    let heightU = Math.round(widthU / PREFERRED_TEXT_NOTE_ASPECT_RATIO);
    let width = widthU * unit;
    let height = heightU * unit;

    // Adjust the height
    testRect.setSize(new Size(width, height));
    let textLayout = calculateTextLayout(text, note.textRect(), noteFont);
    while (testRect.width >= MIN_NOTE_WIDTH && testRect.height >= MIN_NOTE_HEIGHT) {
        if (textLayout.isElided) {
            break;
        } else {
            height = testRect.height;
        }

        testRect.setSize(new Size(testRect.width, testRect.height - unit));
        textLayout = calculateTextLayout(text, note.textRect(), noteFont);
    }

    // Adjust the width. We check for changes in the text, because
    // even elided text (if it's multi line) can have empty space laterally
    let textBeforeAdjust = textLayout.text();
    text = textBeforeAdjust;
    testRect.setSize(new Size(width, height));
    while (testRect.width >= MIN_NOTE_WIDTH && testRect.height >= MIN_NOTE_HEIGHT) {
        if (text !== textBeforeAdjust) {
            break;
        } else {
            width = testRect.width;
        }

        testRect.setSize(new Size(testRect.width - unit, testRect.height));
        textLayout = calculateTextLayout(text, note.textRect(), noteFont);
        text = textLayout.text();
    }

    return new Size(width, height);
}

