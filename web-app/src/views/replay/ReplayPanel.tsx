import React, { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { ReplayControls } from "@/views/replay/ReplayControls";
import { ReplayPanelViewState } from "@/views/replay/ReplayViewState";
import { replayActions } from "@/actions/replay";
import { pamet } from "@/app/facade";
import { buildReplayIndex } from "@/procedures/replay";
import "@/views/replay/ReplayPanel.css";

/**
 * Floating panel for replay controls, rendered inside the panel-layer.
 * Styled to match the existing top-left/top-right panels.
 */
export const ReplayPanel = observer(({
    state,
}: {
    state: ReplayPanelViewState;
}) => {
    useEffect(() => {
        void buildReplayIndex();
    }, []);

    const stopPropagation = (e: React.MouseEvent) => e.stopPropagation();
    const stopTouchPropagation = (e: React.TouchEvent) => e.stopPropagation();

    return (
        <div
            className="replay-panel"
            onClick={stopPropagation}
            onMouseDown={stopPropagation}
            onMouseUp={stopPropagation}
            onMouseMove={stopPropagation}
            onTouchStart={stopTouchPropagation}
            onTouchMove={stopTouchPropagation}
            onTouchEnd={stopTouchPropagation}
        >
            <ReplayControls state={state} />
            {state.indexStale && (
                <button
                    className="replay-panel-btn reindex-btn"
                    onClick={() => buildReplayIndex()}
                    title="New commits detected — rebuild index"
                >
                    Reindex
                </button>
            )}
            <button
                className="replay-panel-close"
                onClick={() => {
                    pamet.replayService.stopPlayback();
                    replayActions.hideHistoryPage(pamet.appViewState);
                    replayActions.closeReplay(pamet.appViewState);
                }}
                title="Close replay"
            >
                ✕
            </button>
        </div>
    );
});
