
import { FC, useMemo } from 'react';
import { color_role_to_hex_color } from "../../util/Color";
import { ArrowViewState, BezierCurve } from './ArrowViewState';

export interface ArrowProps {
    arrowViewState: ArrowViewState;
    clickHandler?: (event: React.MouseEvent<SVGPathElement, MouseEvent>) => void;
}

export const ArrowComponent: FC<ArrowProps> = ({ arrowViewState, clickHandler }: ArrowProps) => {

    const svg_path = useMemo(() => {
        const curves: BezierCurve[] = arrowViewState.bezierCurveParams;
        const path: string[] = [];
        for (let i = 0; i < curves.length; i++) {
            const curveData = curves[i];
            const bezierCurve = {
                start: curveData[0],
                control1: curveData[1],
                control2: curveData[2],
                end: curveData[3],
            }
            path.push(`M ${bezierCurve.start.x} ${bezierCurve.start.y}`);
            path.push(`C ${bezierCurve.control1.x} ${bezierCurve.control1.y} ${bezierCurve.control2.x} ${bezierCurve.control2.y} ${bezierCurve.end.x} ${bezierCurve.end.y}`);
        }

        return path.join(' ');
    }, [arrowViewState]);

    let arrow = arrowViewState.arrow();
    let color = color_role_to_hex_color(arrow.color_role)
    let line_thickness = arrow.line_thickness;

    return (
        <g>
        <path d={svg_path}
            stroke={color}
            fill="none"
            strokeWidth={line_thickness}
            markerEnd={`url(#arrowhead-${arrow.id})`}
        />
        {/* click path with a wider stroke width */}
        <path d={svg_path}
            stroke="transparent"
            fill="none"
            strokeWidth={line_thickness + 10}
            onClick={clickHandler}
        />
        </g>
    )
}


export const ArrowHeadComponent: FC<ArrowProps> = ({ arrowViewState }) => {

    return (
        <marker id={`arrowhead-${arrowViewState.arrow().id}`}
            markerWidth="10" markerHeight="7"
            refX="10" refY="3.5" orient="auto">

            <polygon points="0 0, 10 3.5, 0 7"
                stroke={color_role_to_hex_color(arrowViewState.arrow().color_role)}
            />
        </marker>
    )
}
