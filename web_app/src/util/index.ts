import { Point2D } from "./Point2D";

export type Color = [number, number, number, number];
export type SelectionDict = { [key: string]: boolean };


export function color_to_css_rgba_string(color: Color){
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
