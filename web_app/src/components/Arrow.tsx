import { ArrowData } from "../types/Arrow";

import React, { FC, useMemo } from 'react';
import { Point2D } from "../util/Point2D";
import { color_to_css_rgba_string } from "../util";

export enum ArrowAnchorType {
    NONE = 'none',
    AUTO = 'auto',
    MID_LEFT = 'mid_left',
    TOP_MID = 'top_mid',
    MID_RIGHT = 'mid_right',
    BOTTOM_MID = 'bottom_mid',
}

export interface ArrowProps {
    arrowData: ArrowData;
}

const ARROW_HAND_LENGTH = 20;
const SLOPE_POINT_DISTANCE = ARROW_HAND_LENGTH / 2;
const ARROW_HAND_ANGLE = 25;  // Degrees

export const ArrowComponent: FC<ArrowProps> = ({ arrowData }) => {

    const svg_path = useMemo(() => {
        const curves = arrowData.cache.curves;
        const path: string[] = [];
        for (let i = 0; i < curves.length; i++) {
            const curveData = curves[i];
            const bezierCurve = {
                start: new Point2D(curveData[0][0], curveData[0][1]),
                control1: new Point2D(curveData[1][0], curveData[1][1]),
                control2: new Point2D(curveData[2][0], curveData[2][1]),
                end: new Point2D(curveData[3][0], curveData[3][1]),
            }
            path.push(`M ${bezierCurve.start.x} ${bezierCurve.start.y}`);
            path.push(`C ${bezierCurve.control1.x} ${bezierCurve.control1.y} ${bezierCurve.control2.x} ${bezierCurve.control2.y} ${bezierCurve.end.x} ${bezierCurve.end.y}`);
        }

        return path.join(' ');
    }, [arrowData]);

    let color = color_to_css_rgba_string(arrowData.color)
    let line_thickness = arrowData.line_thickness;

    return (
            <path d={svg_path}
                stroke={color}
                fill="none"
                strokeWidth={line_thickness}
                markerEnd={`url(#arrowhead-${arrowData.id})`}
            />
    )
}


export const ArrowHeadComponent: FC<ArrowProps> = ({ arrowData }) => {

    return (
        <marker id={`arrowhead-${arrowData.id}`}
        markerWidth="10" markerHeight="7"
        refX="10" refY="3.5" orient="auto">

        <polygon points="0 0, 10 3.5, 0 7"
          stroke={color_to_css_rgba_string(arrowData.color)}
        />
      </marker>
    )
}
