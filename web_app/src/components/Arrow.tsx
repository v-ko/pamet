
import { FC, useMemo } from 'react';
import { Point2D } from "../util/Point2D";
import { color_to_css_rgba_string } from "../util";
import { ArrowViewState } from './ArrowViewState';

export interface ArrowProps {
    arrow: ArrowViewState;
}

const ARROW_HAND_LENGTH = 20;
const SLOPE_POINT_DISTANCE = ARROW_HAND_LENGTH / 2;
const ARROW_HAND_ANGLE = 25;  // Degrees


export const ArrowComponent: FC<ArrowProps> = ({ arrow: arrowViewState }: ArrowProps) => {

    const svg_path = useMemo(() => {
        const curves = arrowViewState.bezierCurveParams;
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
    }, [arrowViewState]);

    let color = color_to_css_rgba_string(arrowViewState.color)
    let line_thickness = arrowViewState.line_thickness;

    return (
        <path d={svg_path}
            stroke={color}
            fill="none"
            strokeWidth={line_thickness}
            markerEnd={`url(#arrowhead-${arrowViewState.id})`}
        />
    )
}


export const ArrowHeadComponent: FC<ArrowProps> = ({ arrow }) => {

    return (
        <marker id={`arrowhead-${arrow.id}`}
            markerWidth="10" markerHeight="7"
            refX="10" refY="3.5" orient="auto">

            <polygon points="0 0, 10 3.5, 0 7"
                stroke={color_to_css_rgba_string(arrow.color)}
            />
        </marker>
    )
}
