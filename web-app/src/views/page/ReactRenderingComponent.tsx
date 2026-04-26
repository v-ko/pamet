// @ts-nocheck

import React from "react";

import { PageViewState } from "@/views/page/PageViewState";
import { NoteComponent } from "@/components/note/Note";
import { ArrowComponent, ArrowHeadComponent } from "@/views/arrow/Arrow";
import { observer } from "mobx-react-lite";

const canvasWrapperStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    transform: 'scale(var(--map-scale)) translate(var(--map-translate-x), var(--map-translate-y))',
    backfaceVisibility: 'hidden', // Fixes rendering artefact bug
    touchAction: 'none',
    userSelect: 'none',
};

export const CanvasReactComponent = observer(({state}: {state: PageViewState}) => {

    // Those are needed for the React note rendering
    let vb_x = -100000;
    let vb_y = -100000;
    let vb_width = 200000;
    let vb_height = 200000;

    return (
        <div
            style={{
                ...canvasWrapperStyle,
                '--map-scale': state.viewport.heightScaleFactor(),
                '--map-translate-x': -state.viewport.xReal + 'px',
                '--map-translate-y': -state.viewport.yReal + 'px',
            }}
        >

            {Array.from(state.noteViewStatesById.values()).map((noteViewState) => (
                <NoteComponent
                    key={noteViewState.note().id}
                    noteViewState={noteViewState}
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
                    {Array.from(state.arrowViewStatesById.values()).map((arrowVS) => (
                        <ArrowHeadComponent key={arrowVS.arrow().id} arrowViewState={arrowVS} />
                    ))}
                </defs>
                {Array.from(state.arrowViewStatesById.values()).map((arrowVS) => (
                    <ArrowComponent
                        key={arrowVS.arrow().id}
                        arrowViewState={arrowVS}
                        clickHandler={() => { console.log('Arrow clicked', arrowVS.arrow().id) }}
                    />
                ))}
            </svg>
        </div>
    )
});
