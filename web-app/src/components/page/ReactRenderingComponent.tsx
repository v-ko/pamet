import React from "react";
import styled from 'styled-components';

import { PageViewState } from "./PageViewState";
import { NoteComponent } from "../note/Note";
import { ArrowComponent, ArrowHeadComponent } from "../arrow/Arrow";
import { observer } from "mobx-react-lite";

export const CanvasWrapper = styled.div`

width: ${props => props.viewport.geometry[2]}px;
height: ${props => props.viewport.geometry[3]}px;
width: 100%;
height: 100%;

transform:  scale(var(--map-scale)) translate(var(--map-translate-x), var(--map-translate-y));
backface-visibility: hidden;  // Fixes rendering artefact bug

// Transitions are very inefficient (at small scale coefficients)
// So we disable them for now
/* ${props => props.transformTransitionDuration > 0 ?
        `transition: transform ${props.transformTransitionDuration}s;` : ''} */
touch-action: none;
user-select: none;
`;

export const CanvasReactComponent = observer(({state}: {state: PageViewState}) => {

    // Those are needed for the React note rendering
    let vb_x = -100000;
    let vb_y = -100000;
    let vb_width = 200000;
    let vb_height = 200000;

    return (
        <CanvasWrapper
            viewport={state.viewport}
            // transformTransitionDuration={viewportTransitionDuration}
            style={{
                '--map-scale': state.viewport.heightScaleFactor(),
                '--map-translate-x': -state.viewport.xReal + 'px',
                '--map-translate-y': -state.viewport.yReal + 'px',
                // '--map-translate-x': -state.viewport.center.x + 'px',
                // '--map-translate-y': -state.viewport.center.y + 'px',
            }}
        >

            {Array.from(state.noteViewStatesByOwnId.values()).map((noteViewState) => (
                <NoteComponent
                    key={noteViewState.note().id}
                    noteViewState={noteViewState}
                    // handleClick={(event) => { handleClickOnNote(event, noteViewState) }}
                    />
            ))}

            <svg
                viewBox={`${vb_x} ${vb_y} ${vb_width} ${vb_height}`}
                style={{
                    position: 'absolute',
                    left: `${vb_x}`,
                    top: `${vb_y}`,
                    width: `${vb_width}`,
                    height: `${vb_height}`,
                    pointerEvents: 'none',
                    outline: '100px solid red',
                }}
            >
                <defs>
                    {Array.from(state.arrowViewStatesByOwnId.values()).map((arrowVS) => (
                        <ArrowHeadComponent key={arrowVS.arrow().id} arrowViewState={arrowVS} />
                    ))}
                </defs>
                {Array.from(state.arrowViewStatesByOwnId.values()).map((arrowVS) => (
                    <ArrowComponent
                        key={arrowVS.arrow().id}
                        arrowViewState={arrowVS}
                        clickHandler={(event) => { console.log('Arrow clicked', arrowVS.arrow().id) }}
                    />
                ))}
            </svg>
        </CanvasWrapper>
    )
});
