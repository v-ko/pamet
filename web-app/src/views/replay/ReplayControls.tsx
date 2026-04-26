import { useState, useRef, useCallback, useEffect } from "react";
import { observer } from "mobx-react-lite";
import { ReplayTimelineCanvas } from "@/views/replay/ReplayTimelineCanvas";
import { ReplayPanelViewState } from "@/views/replay/ReplayViewState";
import { pamet } from "@/app/facade";
import { replayActions } from "@/actions/replay";
import "@/views/replay/ReplayControls.css";

export const ReplayControls = observer(({
    state,
}: {
    state: ReplayPanelViewState;
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [containerWidth, setContainerWidth] = useState(600);

    // Selection range as fractions [0..1]
    const [selFracStart, setSelFracStart] = useState(0);
    const [selFracEnd, setSelFracEnd] = useState(1);

    // Dragging handle state
    const [dragging, setDragging] = useState<"start" | "end" | null>(null);

    const { commitMarkers, rangeStart, rangeEnd, playing, currentMarkerIdx } = state;
    const commitTimestamps = commitMarkers.map(m => m.timestamp);

    /** Seek to a specific marker index, update store + history PVS + playhead. */
    const seekToMarker = useCallback((idx: number) => {
        const pageId = pamet.appViewState.currentPageId;
        if (!pageId || idx < 0 || idx >= commitMarkers.length) return;
        // Seeking to the last (most recent) commit returns to the live page
        if (idx === commitMarkers.length - 1) {
            replayActions.hideHistoryPage(pamet.appViewState);
            state.currentMarkerIdx = -1;
            return;
        }
        pamet.replayService.seekSnapshot(commitMarkers[idx].id, pageId);
        replayActions.showHistoryPage(pamet.appViewState, pamet.historyStore, pageId);
        state.currentMarkerIdx = idx;
    }, [commitMarkers, state]);

    /** Callback passed to startPlayback — updates PVS + playhead each tick. */
    const onPlaybackTick = useCallback((commitId: string) => {
        const pageId = pamet.appViewState.currentPageId;
        if (!pageId) return;
        replayActions.showHistoryPage(pamet.appViewState, pamet.historyStore, pageId);
        const idx = commitMarkers.findIndex(m => m.id === commitId);
        if (idx >= 0) state.currentMarkerIdx = idx;
    }, [commitMarkers, state]);

    // Measure container width
    useEffect(() => {
        const el = containerRef.current;
        if (!el) return;
        const ro = new ResizeObserver((entries) => {
            for (const entry of entries) {
                setContainerWidth(entry.contentRect.width);
            }
        });
        ro.observe(el);
        return () => ro.disconnect();
    }, []);

    const span = rangeEnd - rangeStart;

    // Compute the marker indices within the selection range
    const selStartTs = rangeStart + selFracStart * span;
    const selEndTs = rangeStart + selFracEnd * span;
    const markersInRange = commitMarkers
        .map((m, i) => ({ ...m, idx: i }))
        .filter(m => m.timestamp >= selStartTs && m.timestamp <= selEndTs);
    const firstInRange = markersInRange.length > 0 ? markersInRange[0] : null;
    const lastInRange = markersInRange.length > 0 ? markersInRange[markersInRange.length - 1] : null;

    // Compute playhead position as timeline fraction
    const playheadFrac = (() => {
        if (commitMarkers.length === 0 || currentMarkerIdx < 0) return undefined;
        if (currentMarkerIdx >= commitMarkers.length) return undefined;
        const ts = commitMarkers[currentMarkerIdx].timestamp;
        if (span <= 0) return 0;
        return (ts - rangeStart) / span;
    })();

    // Format selection times for display
    const fmtTime = (frac: number) => {
        const ms = rangeStart + frac * span;
        if (ms <= 0) return "—";
        const d = new Date(ms);
        return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
    };

    // Handle drag
    const handlePointerDown = useCallback((which: "start" | "end") => (e: React.PointerEvent) => {
        e.preventDefault();
        e.stopPropagation();
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
        setDragging(which);
    }, []);

    const handlePointerMove = useCallback((e: React.PointerEvent) => {
        if (!dragging || !containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        let frac = (e.clientX - rect.left) / rect.width;
        frac = Math.max(0, Math.min(1, frac));

        if (dragging === "start") {
            setSelFracStart(Math.min(frac, selFracEnd - 0.005));
        } else {
            setSelFracEnd(Math.max(frac, selFracStart + 0.005));
        }
    }, [dragging, selFracStart, selFracEnd]);

    const handlePointerUp = useCallback(() => {
        setDragging(null);
    }, []);

    // Timeline click → seek to nearest relevant commit
    const handleTimelineClick = useCallback((e: React.MouseEvent) => {
        if (dragging) return;
        if (!containerRef.current || commitMarkers.length === 0) return;
        const rect = containerRef.current.getBoundingClientRect();
        const frac = (e.clientX - rect.left) / rect.width;
        const timestamp = rangeStart + frac * span;

        // Find closest marker
        let bestIdx = 0;
        let bestDist = Math.abs(commitMarkers[0].timestamp - timestamp);
        for (let i = 1; i < commitMarkers.length; i++) {
            const dist = Math.abs(commitMarkers[i].timestamp - timestamp);
            if (dist < bestDist) {
                bestDist = dist;
                bestIdx = i;
            }
        }

        // Clicking the last (most recent) commit returns to the live page
        if (bestIdx === commitMarkers.length - 1) {
            replayActions.hideHistoryPage(pamet.appViewState);
            state.currentMarkerIdx = -1;
            return;
        }

        if (bestIdx !== currentMarkerIdx) {
            seekToMarker(bestIdx);
        }
    }, [rangeStart, span, dragging, commitMarkers, currentMarkerIdx, seekToMarker]);

    const timelineHeight = 40;

    if (commitMarkers.length === 0) {
        return (
            <div className="replay-controls">
                <div className="replay-controls-loading">No history available for this page.</div>
            </div>
        );
    }

    return (
        <div
            className="replay-controls"
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
        >
            {/* Left: transport buttons + count */}
            <div className="replay-controls-buttons">
                <button
                    className="replay-btn"
                    onClick={() => seekToMarker(currentMarkerIdx - 1)}
                    title="Previous commit"
                    disabled={playing || currentMarkerIdx <= 0}
                >
                    ⏮
                </button>
                {playing ? (
                    <button
                        className="replay-btn replay-btn-play"
                        onClick={() => {
                            pamet.replayService.stopPlayback();
                            replayActions.hideHistoryPage(pamet.appViewState);
                            replayActions.setReplayPlaying(state, false);
                        }}
                        title="Stop"
                    >
                        ⏹
                    </button>
                ) : (
                    <>
                        <button
                            className="replay-btn replay-btn-play"
                            onClick={() => {
                                const pageId = pamet.appViewState.currentPageId;
                                if (!pageId || !firstInRange || !lastInRange) return;
                                const startIdx = currentMarkerIdx >= firstInRange.idx && currentMarkerIdx <= lastInRange.idx
                                    ? currentMarkerIdx : lastInRange.idx;
                                replayActions.setReplayPlaying(state, true);
                                pamet.replayService.startPlayback(
                                    pageId, commitMarkers[startIdx].id, commitMarkers[firstInRange.idx].id,
                                    'reverse', onPlaybackTick, state.intervalMs,
                                );
                            }}
                            title="Play reversed"
                        >
                            ◀
                        </button>
                        <button
                            className="replay-btn replay-btn-play"
                            onClick={() => {
                                const pageId = pamet.appViewState.currentPageId;
                                if (!pageId || !firstInRange || !lastInRange) return;
                                const startIdx = currentMarkerIdx >= firstInRange.idx && currentMarkerIdx <= lastInRange.idx
                                    ? currentMarkerIdx : firstInRange.idx;
                                replayActions.setReplayPlaying(state, true);
                                pamet.replayService.startPlayback(
                                    pageId, commitMarkers[startIdx].id, commitMarkers[lastInRange.idx].id,
                                    'forward', onPlaybackTick, state.intervalMs,
                                );
                            }}
                            title="Play forward"
                        >
                            ▶
                        </button>
                    </>
                )}
                <button
                    className="replay-btn"
                    onClick={() => seekToMarker(currentMarkerIdx + 1)}
                    title="Next commit"
                    disabled={playing || currentMarkerIdx >= commitMarkers.length - 1}
                >
                    ⏭
                </button>
                <span className="replay-commit-count" title="Commits to replay">
                    Count: {commitMarkers.length}
                </span>
                <label className="replay-delay-label" title="Animation delay between steps (ms)">
                    Delay:
                    <input
                        type="number"
                        className="replay-delay-input"
                        min={50}
                        max={5000}
                        step={50}
                        value={state.intervalMs}
                        onChange={(e) => { state.intervalMs = Math.max(50, Number(e.target.value) || 300); }}
                        disabled={playing}
                    />
                    ms
                </label>
            </div>

            {/* Right: timeline area */}
            <div className="replay-timeline-area" ref={containerRef} onClick={handleTimelineClick}>
                <ReplayTimelineCanvas
                    commitTimestamps={commitTimestamps}
                    rangeStart={rangeStart}
                    rangeEnd={rangeEnd}
                    selFracStart={selFracStart}
                    selFracEnd={selFracEnd}
                    width={containerWidth}
                    height={timelineHeight}
                    playheadFrac={playheadFrac}
                />

                {/* Selection range handles */}
                <div
                    className="replay-range-handle replay-range-handle-start"
                    style={{ left: `${selFracStart * 100}%` }}
                    onPointerDown={handlePointerDown("start")}
                />
                <div
                    className="replay-range-handle replay-range-handle-end"
                    style={{ left: `${selFracEnd * 100}%` }}
                    onPointerDown={handlePointerDown("end")}
                />

                {/* Selection range labels */}
                <div className="replay-range-labels">
                    <span style={{ left: `${selFracStart * 100}%` }} className="replay-range-label">
                        {fmtTime(selFracStart)}
                    </span>
                    <span style={{ left: `${selFracEnd * 100}%` }} className="replay-range-label">
                        {fmtTime(selFracEnd)}
                    </span>
                </div>
            </div>
        </div>
    );
});
