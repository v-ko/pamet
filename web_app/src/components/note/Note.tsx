import { useEffect, useMemo, useRef } from 'react';
import styled from 'styled-components';
import { NOTE_MARGIN } from '../../constants';
import { MapController } from '../../controllers/MapController';
import { Note } from '../../model/Note';
import { NoteData } from '../../types/Note';
import { SelectionDict } from '../../types/util';
import { color_to_css_rgba_string } from '../../util';
import { Rectangle } from '../../util/Rectangle';

interface NoteComponentProps {
    noteData: NoteData;
    selected: boolean;
    mapController: MapController;
}

export const NoteContainer = styled.a`
    text-decoration: none;
    position: absolute;
    display: flex;
    flex-wrap: wrap;
    top: ${props => props.y}px;
    left: ${props => props.x}px;
    width: ${props => props.width}px;
    height: ${props => props.height}px;
    color: ${props => props.color};
    background-color: ${props => props.backgroundColor};
    ${props => props.isLink ? `border: 1px solid ${props.color}` : ''}
`;

const NoteText = styled.div`
    flex-grow: 8;
    align-self: center;
    min-height: 20px;
    min-width: 20px;
    width: min-content;
    height: min-content;

    overflow: hidden;
    text-decoration: none;

    //justify text in center
    display: flex;
    text-align: center;
    align-items: center;
    justify-content: center;

    font-family: 'Open Sans', sans-serif;
    font-size: 18px;
    line-height: 20px;
    color: ${props => props.color};
`;

const NoteImage = styled.img`
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    object-position: top left;
`;

let EMPTY_LINE = '';

class TextLayout {
    data: [string, Rectangle][] = [];
    is_elided: boolean = false;
    align: string = 'center';

    text(): string {
        return this.data.join('\n');
    }
}

// def elide_text(text, text_rect: Rectangle, font: QFont) -> TextLayout:
//     font_metrics = QFontMetrics(font)

//     # Get the needed parameters
//     line_spacing = NO_SCALE_LINE_SPACING

//     # Replace tabs with spaces
//     text = text.replace('\t', '    ')

//     # Get the y coordinates of the lines
//     line_vpositions = []
//     line_y = text_rect.top()
//     while line_y <= text_rect.bottom() - line_spacing:
//         line_vpositions.append(line_y)
//         line_y += line_spacing

// !!! UNTESTED !!!
// Work left:
// Implement a React context for the canvas (or pass a ref from the map page)
// Finish the effect for calculating the elided text
// Implement the TSX code for rendering the text
function calculateTextLayout(text: string, text_rect: Rectangle, canvas: HTMLCanvasElement): TextLayout {
    // Only QFontMetrics.horizontalAdvance() needs to be susbstituted with
    // canvas.measureText().width
    // Init the canvas
    let ctx = canvas.getContext('2d');
    if (!ctx) {
        throw new Error('Failed to get canvas context');
    }

    // Get the needed parameters
    let line_spacing = 20;

    // Replace tabs with spaces
    text = text.replace('\t', '    ');

    // Get the y coordinates of the lines
    let line_vpositions: number[] = [];
    let line_y = text_rect.top();
    while (line_y <= (text_rect.bottom() - line_spacing)) {
        line_vpositions.push(line_y);
        line_y += line_spacing;
    }

    //     # Divide the text into words and "mark" the ones ending with am
    //     # EoL char (by keeping their indexes in eol_word_indices)
    //     words = []
    //     eol_word_indices = []
    //     for line in text.split('\n'):
    //         if not line:
    //             words.append(EMPTY_LINE)
    //             eol_word_indices.append(len(words) - 1)
    //             continue
    //         words_on_line = line.split(' ')
    //         words.extend(words_on_line)
    //         eol_word_indices.append(len(words) - 1)

    // Divide the text into words and "mark" the ones ending with am
    // EoL char (by keeping their indexes in eol_word_indices)
    let words: string[] = [];
    let eol_word_indices: number[] = [];
    for (let line of text.split('\n')) {
        if (!line) {
            words.push(EMPTY_LINE);
            eol_word_indices.push(words.length - 1);
            continue;
        }
        let words_on_line = line.split(' ');
        words = words.concat(words_on_line);
        eol_word_indices.push(words.length - 1);
    }

    //     text_layout = TextLayout()

    //     # In case for some reason the text rect is too small to fit any text
    //     if not line_vpositions and text:
    //         text_layout.is_elided = True
    //         return text_layout

    //     ellide_line_end = False
    //     word_reached_idx = 0
    //     ellipsis_width = font_metrics.boundingRect('...').width()

    let text_layout = new TextLayout();

    // In case for some reason the text rect is too small to fit any text
    if (!line_vpositions.length && text) {
        text_layout.is_elided = true;
        return text_layout;
    }

    // If there's a line break in the text: mark the alignment as left
    if (text.includes('\n')) {
        text_layout.align = 'left';
    }

    let ellide_line_end = false;
    let word_reached_idx = 0;
    let ellipsis_width = ctx.measureText('...').width;

    //     # Start filling the available lines one by one
    //     for line_idx, line_y in enumerate(line_vpositions):
    //         words_left = words[word_reached_idx:]

    //         # Find the coordinates and dimentions of the line
    //         line_rect = QRectF(*text_rect.as_tuple())
    //         line_rect.moveTop(line_y)
    //         line_rect.setHeight(line_spacing)

    //         # Fill the line word by word
    //         words_on_line = []
    //         width_left = text_rect.width()
    //         used_words = 0

    // Start filling the available lines one by one
    for (let line_idx = 0; line_idx < line_vpositions.length; line_idx++) {
        let line_y = line_vpositions[line_idx];
        let words_left = words.slice(word_reached_idx);

        // Find the coordinates and dimentions of the line
        let line_rect = new Rectangle(text_rect.left(), line_y, text_rect.width(), line_spacing);

        // Fill the line word by word
        let words_on_line: string[] = [];
        let width_left = text_rect.width();
        let used_words = 0;

        //         for word_idx_on_line, word in enumerate(words_left):
        //             # Add a leading space except before the first word
        //             if word_idx_on_line != 0:
        //                 word = ' ' + word

        //             at_the_last_line = line_idx == (len(line_vpositions) - 1)
        //             at_last_word = word_idx_on_line == (len(words_left) - 1)

        //             # Get the dimentions of the word if drawn
        //             # word_bbox = font_metrics.boundingRect(word)
        //             horizontal_advance = font_metrics.horizontalAdvance(word)

        for (let word_idx_on_line = 0; word_idx_on_line < words_left.length; word_idx_on_line++) {
            // Add a leading space except before the first word
            if (word_idx_on_line != 0) {
                words_left[word_idx_on_line] = ' ' + words_left[word_idx_on_line];
            }

            let at_the_last_line = line_idx == line_vpositions.length - 1;
            let at_last_word = word_idx_on_line == words_left.length - 1;

            // Get the dimentions of the word if drawn
            // word_bbox = font_metrics.boundingRect(word)
            let horizontal_advance = ctx.measureText(words_left[word_idx_on_line]).width;

            //             # There's enough space on the line for the next word
            //             if width_left >= horizontal_advance:
            //                 width_left -= horizontal_advance
            //                 words_on_line.append(word)
            //                 used_words += 1

            //             else:  # There's not enough space for the next word

            //                 # If there's no room to add an elided word - ellide the
            //                 # previous
            //                 if at_the_last_line and width_left < ellipsis_width:
            //                     # words_on_line[-1] = words_on_line[-1]
            //                     ellide_line_end = True

            //                 # Elide if we're past the end of the last line
            //                 # or if it's the first word on the line and it's just too long
            //                 if at_the_last_line or word_idx_on_line == 0:
            //                     word = font_metrics.elidedText(word, Qt.ElideRight,
            //                                                    width_left)
            //                     text_layout.is_elided = True
            //                     words_on_line.append(word)
            //                     used_words += 1

            //                 # Done with this line - break and start the next if any
            //                 break

            if (width_left >= horizontal_advance) {
                width_left -= horizontal_advance;
                words_on_line.push(words_left[word_idx_on_line]);
                used_words += 1;
            } else {
                // If there's no room to add an elided word - ellide the
                // previous
                if (at_the_last_line && width_left < ellipsis_width) {
                    // words_on_line[-1] = words_on_line[-1]
                    ellide_line_end = true;
                }

                const elideWord = (word: string, target_width: number, ctx: CanvasRenderingContext2D) => {
                    // Add an ellipsis to the end of the word
                    let ellipsis = '...';
                    let ellipsis_width = ctx.measureText(ellipsis).width;
                    let word_width = ctx.measureText(word).width;
                    let width_left = target_width - word_width - ellipsis_width;
                    if (target_width <= ellipsis_width) {
                        return ellipsis;
                    }

                    // Go through ellipsis positions to find the first that fits
                    // Start from the end of the word and go backwards
                    let ellipsis_pos = word.length;
                    while (ellipsis_pos > 0) {
                        let word_part = word.slice(0, ellipsis_pos);
                        let word_part_width = ctx.measureText(word_part).width;
                        if (word_part_width <= width_left) {
                            return word_part + ellipsis;
                        }
                        ellipsis_pos -= 1;
                    }
                    return ellipsis;
                };

                // Elide if we're past the end of the last line
                // or if it's the first word on the line and it's just too long
                if (at_the_last_line || word_idx_on_line == 0) {
                    let word = elideWord(words_left[word_idx_on_line], width_left, ctx);
                    text_layout.is_elided = true;
                    words_on_line.push(word);
                    used_words += 1;
                }

                // Done with this line - break and start the next if any
                break;
            }

            //             # Check if we're on EoL (because of a line break in the text)
            //             if (word_reached_idx + word_idx_on_line) in eol_word_indices:
            //                 if at_the_last_line and not at_last_word:
            //                     ellide_line_end = True
            //                 break

            //         if not words_left:
            //             break

            //         word_reached_idx += used_words
            //         line_text = ''.join(words_on_line)

            //         if ellide_line_end:
            //             text_layout.is_elided = True
            //             if len(line_text) >= 3:
            //                 line_text = line_text[:-3] + '...'
            //             else:
            //                 line_text = '...'

            // Check if we're on EoL (because of a line break in the text)
            if (eol_word_indices.includes(word_reached_idx + word_idx_on_line)) {
                if (at_the_last_line && !at_last_word) {
                    ellide_line_end = true;
                }
                break;
            }
        }

        if (!words_left) {
            break;
        }

        word_reached_idx += used_words;
        let line_text = words_on_line.join('');

        if (ellide_line_end) {
            text_layout.is_elided = true;
            if (line_text.length >= 3) {
                line_text = line_text.slice(0, -3) + '...';
            } else {
                line_text = '...';
            }
        }

        //         text_layout.data.append((line_text, line_rect))
        //     return text_layout

        text_layout.data.push([line_text, line_rect]);
    }
    return text_layout;
}

export const NoteComponent = ({ noteData, selected, mapController }: NoteComponentProps) => {

    // const [textLayout, setTextLayout] = useState<TextLayout>(new TextLayout());
    // const canvas = useContext(CanvasContext) as HTMLCanvasElement;
    // const elideText = useMemo(() => {
    //     let errorLayout = new TextLayout()
    //     errorLayout.data = [['Error', new Rectangle(0, 0, 20, 50)]]
    //     if (!canvas) {
    //         return errorLayout;
    //     }
    //     const ctx = canvas.getContext('2d');
    //     if (!ctx) {
    //         return errorLayout;
    //     }

    //     const text = noteData.content.text;
    //     const text_rect =
    //     setElidedText(calculateTextLayout())
    // }, [])

    const self_ref = useRef<HTMLAnchorElement>(null);
    const note = useMemo(() => {
        return new Note(noteData);
    }, [noteData]);

    const handleClickEvent = (event: MouseEvent) => {
        // if control pressed or shift pressed, add to selection else
        // clear selection and select this note
        if (!(event.ctrlKey || event.shiftKey)) {
        mapController.clearSelection();
        }
        mapController.updateSelection({[noteData.own_id]: true})
    }

    const [x, y, width, height] = noteData.geometry;
    const color = color_to_css_rgba_string(noteData.style.color)
    const backgroundColor = color_to_css_rgba_string(noteData.style.background_color)
    const imageUrl = noteData.content.image_url;

    let isExternal = true;

    // If the url is with a pamet:/ schema - convert it to a local file path
    let href  = noteData.content.url;
    if (href && href.startsWith('pamet:/')) {
        href = href.replace('pamet:/', '/');
        isExternal = false;
    }

    let target: string = '_self';
    if (isExternal) {
        target = '_blank';
    }

    let noteText = noteData.cache?.text_layout_data.lines.join('\n')
    if (imageUrl && noteText) {
        console.log('Image url', imageUrl)
        console.log('Note text', noteText)
    }

    return (
        <NoteContainer
            ref={self_ref}
            href={href}
            target={target}
            rel="noopener noreferrer"
            className="note"
            x={x}
            y={y}
            width={width}
            height={height}
            color={color}
            backgroundColor={backgroundColor}
            isLink={!!noteData.content.url}
            isExternal={isExternal}
            onClick={handleClickEvent}
        >
            {imageUrl && <img src={imageUrl} alt={"Loading..."} style={{
                maxWidth: "100%",
                maxHeight: "100%",
                objectFit: "contain",
                flexGrow: 1,
                alignSelf: "center",
                objectPosition: "top left"}} />}
            {noteText && <NoteText
                color={color}
                padding={NOTE_MARGIN}
            >
                 {noteText}
            </NoteText>}

            {/* Draw a div with a yellow border around the selected note */}
            {/* do not use a custom component, just vanilla div and css-in-js*/}
            {selected && <div
                style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    border: '4px solid yellow',
                }}
            />}


        </NoteContainer>
    );
}
