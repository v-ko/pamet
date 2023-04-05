import { Color } from "../types/util";

export function color_to_css_rgba_string(color: Color){
    // Convert from [0, 1] to [0, 255]. The alpha channel stays in [0, 1]!
    let r = Math.round(color[0] * 255)
    let g = Math.round(color[1] * 255)
    let b = Math.round(color[2] * 255)
    let color_string = `rgba(${r}, ${g}, ${b}, ${color[3]})`
    return color_string
}
