import { makeObservable, observable } from "mobx";

export interface CommitMarker {
    id: string;
    timestamp: number;
}

const MIN_RANGE_SPAN_MS = 4 * 60 * 60 * 1000; // 4 hours

/**
 * Observable state for the replay panel.
 *
 * Holds UI state for the timeline, playback, and indexing.
 * The page view state and service are owned by the facade.
 */
export class ReplayPanelViewState {
    /** Epoch ms — earliest commit timestamp (padded for display). */
    rangeStart: number = 0;
    /** Epoch ms — latest commit timestamp (padded for display). */
    rangeEnd: number = 0;

    /** Page-relevant commit markers in chronological order. */
    commitMarkers: CommitMarker[] = [];

    /** The project ID the current index was built for. */
    indexedProjectId: string | null = null;

    /** True when new commits have been made since the last indexing. */
    indexStale: boolean = false;

    /** Current position in commitMarkers.
     *  -1 means no position set yet. */
    currentMarkerIdx: number = -1;

    /** True while auto-playback is running. */
    playing: boolean = false;

    /** Delay between animation steps in ms. */
    intervalMs: number = 300;

    constructor() {
        makeObservable(this, {
            rangeStart: observable,
            rangeEnd: observable,
            commitMarkers: observable.ref,
            indexedProjectId: observable,
            indexStale: observable,
            currentMarkerIdx: observable,
            playing: observable,
            intervalMs: observable,
        });
    }

    /** Update commit markers and recompute the display range. */
    setCommitMarkers(markers: CommitMarker[]) {
        this.commitMarkers = markers;
        if (markers.length === 0) {
            this.rangeStart = 0;
            this.rangeEnd = 0;
            return;
        }
        const first = markers[0].timestamp;
        const last = markers[markers.length - 1].timestamp;
        const span = last - first;
        if (span < MIN_RANGE_SPAN_MS) {
            const pad = (MIN_RANGE_SPAN_MS - span) / 2;
            this.rangeStart = first - pad;
            this.rangeEnd = last + pad;
        } else {
            this.rangeStart = first;
            this.rangeEnd = last;
        }
    }
}
