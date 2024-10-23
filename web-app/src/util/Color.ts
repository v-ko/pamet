import { COLOR_ROLE_MAP } from "../core/constants";

export type RGBAColorData = [number, number, number, number];
export type HexColorData = string;

export function color_to_css_rgba_string(color: RGBAColorData) {
    // Convert from [0, 1] to [0, 255]. The alpha channel stays in [0, 1]!
    let r = Math.round(color[0] * 255);
    let g = Math.round(color[1] * 255);
    let b = Math.round(color[2] * 255);
    let color_string = `rgba(${r}, ${g}, ${b}, ${color[3]})`;
    return color_string;
}

export function color_role_to_hex_color(color_role: string): HexColorData {
    if (color_role in COLOR_ROLE_MAP) {
        return COLOR_ROLE_MAP[color_role];
    } else {
        throw Error(`Color role ${color_role} not found in color role map`);
    }
}

export function old_color_to_role(rgbaColor: RGBAColorData): string {
    // TODO: Rename this to reflect the app versions of the schema
    /**
     * Convert from rgba normalized values to named roles.
     * This should be used only at dev time and for imports from old data.
     */
    let roleToRgbaMap: Record<string, RGBAColorData> = {
        'primary': [0.0, 0.0, 1.0, 0.1],
        'onPrimary': [0.0, 0.0, 1.0, 1.0],
        'error': [1.0, 0.0, 0.0, 0.1],
        'onError': [1.0, 0.0, 0.0, 1.0],
        'success': [0.0, 1.0, 0.0, 0.1],
        'onSuccess': [0.0, 0.64, 0.235, 1.0],
        'surfaceDim': [0.0, 0.0, 0.0, 0.1],
        'onSurface': [0.0, 0.0, 0.0, 1.0],
        'transparent': [0.0, 0.0, 0.0, 0.0],
    }

    function closestColor(rgba: RGBAColorData): string {
        /**
         * Find the closest color role to the given rgba color.
         *
         * This is a simple distance calculation in the RGBA space, using
         * the Euclidean distance.
         */
        let minDistance = Infinity;
        let closestRole = '';
        for (let role in roleToRgbaMap) {
            let roleRgba = roleToRgbaMap[role];
            let distance = Math.sqrt(
                (rgba[0] - roleRgba[0]) ** 2 +
                (rgba[1] - roleRgba[1]) ** 2 +
                (rgba[2] - roleRgba[2]) ** 2 +
                (rgba[3] - roleRgba[3]) ** 2
            );
            if (distance < minDistance) {
                minDistance = distance;
                closestRole = role;
            }
        }
        return closestRole;
    }

    return closestColor(rgbaColor);
}
