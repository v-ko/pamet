import React, { useEffect } from "react";
import { observer } from "mobx-react-lite";
import { ReplayControls } from "@/views/replay/ReplayControls";
import { ReplayPanelViewState } from "@/views/replay/ReplayViewState";
import { replayActions } from "@/actions/replay";
import { pamet } from "@/app/facade";
import { buildReplayIndex, startIntegrityOp } from "@/procedures/replay";
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

    const op = state.integrityOp;
    const opRunning = op.status === "running";

    const historyOpen = pamet.appViewState.historyPageViewState !== null;
    const currentMarker = state.currentMarkerIdx >= 0
        ? state.commitMarkers[state.currentMarkerIdx]
        : null;

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
            {historyOpen && currentMarker && (
                <div className="replay-panel-commit-id" title={currentMarker.id}>
                    {state.currentMarkerIdx}/{pamet.replayService.index?.allCommits.length ?? '?'} {currentMarker.id.slice(0, 8)}
                </div>
            )}
            {state.indexStale && (
                <button
                    className="replay-panel-btn reindex-btn"
                    onClick={() => buildReplayIndex()}
                    title="New commits detected — rebuild index"
                >
                    Reindex
                </button>
            )}
            {state.hasIntegrityError && (
                <div className="replay-panel-integrity">
                    <div className="integrity-label">⚠ Integrity error detected</div>
                    <div className="integrity-buttons">
                        <button
                            className="replay-panel-btn"
                            disabled={opRunning}
                            onClick={() => startIntegrityOp(state, "checkAllHistory")}
                            title="Check all commits for hash mismatches"
                        >
                            Check All
                        </button>
                        <button
                            className="replay-panel-btn"
                            disabled={opRunning}
                            onClick={() => startIntegrityOp(state, "repairHashes")}
                            title="Re-generate all bad content hashes"
                        >
                            Repair Hashes
                        </button>
                    </div>
                    {opRunning && (
                        <div className="integrity-progress">
                            {op.progressTotal > 0
                                ? <><progress value={op.progressIndex} max={op.progressTotal} /><span>{op.progressIndex} / {op.progressTotal}</span></>
                                : <><progress /><span>Working…</span></>
                            }
                        </div>
                    )}
                    {(op.status === "done" || op.status === "error") && op.resultSummary && (
                        <div className={`integrity-result ${op.status}`}>
                            {op.resultSummary}
                        </div>
                    )}
                </div>
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
