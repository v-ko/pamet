import { AppViewState } from "@/views/AppViewState";
import { getLogger } from "fusion/logging";
import { action } from "fusion/registries/Action";
import { ReplayPanelViewState, CommitMarker, IntegrityOpState } from "@/views/replay/ReplayViewState";
import { BackupPanelViewState } from "@/views/replay/BackupViewState";
import { PageViewState } from "@/views/page/PageViewState";
import { Note } from "@/model/Note";
import { Arrow } from "@/model/Arrow";
import { Page } from "@/model/Page";
import { Store } from "fusion/storage/domain-store/BaseStore";

let log = getLogger("ReplayActions");

class ReplayActions {
    @action
    openReplay(state: AppViewState) {
        if (state.replayPanelVS) {
            log.warning('Replay panel already open');
            return;
        }
        state.replayPanelVS = new ReplayPanelViewState();
    }

    @action
    closeReplay(state: AppViewState) {
        if (!state.replayPanelVS) return;
        state.replayPanelVS = null;
    }

    @action
    openBackups(state: AppViewState) {
        if (state.backupPanelVS) {
            log.warning('Backups panel already open');
            return;
        }
        state.backupPanelVS = new BackupPanelViewState();
    }

    @action
    closeBackups(state: AppViewState) {
        if (!state.backupPanelVS) return;
        state.backupPanelVS = null;
    }

    @action({ issuer: 'service' })
    setReplayIndexStale(replayViewState: ReplayPanelViewState, stale: boolean) {
        replayViewState.indexStale = stale;
    }

    @action({ issuer: 'service' })
    setReplayPlaying(replayViewState: ReplayPanelViewState, playing: boolean) {
        replayViewState.playing = playing;
    }

    @action({ issuer: 'service' })
    updatePanelFromReplayIndex(
        replayViewState: ReplayPanelViewState,
        projectId: string,
        markers: CommitMarker[],
    ) {
        replayViewState.indexedProjectId = projectId;
        replayViewState.indexStale = false;
        replayViewState.setCommitMarkers(markers);
        replayViewState.currentMarkerIdx = markers.length > 0 ? markers.length - 1 : -1;
    }

    @action({ issuer: 'service' })
    showHistoryPage(
        appViewState: AppViewState,
        store: Store,
        pageId: string,
    ) {
        const page = store.findOne({ id: pageId }) as Page | null;
        if (!page) {
            log.warning("showHistoryPage: page not found in history store for", pageId);
            appViewState.historyPageViewState = null;
            return;
        }

        const children = Array.from(store.find({ parentId: pageId }));
        const notes = children.filter(e => e instanceof Note) as Note[];
        const arrows = children.filter(e => e instanceof Arrow) as Arrow[];

        const pvs = new PageViewState(page, notes, arrows);
        pvs.isReplay = true;

        // Copy viewport from existing history overlay (preserves position when
        // switching commits), falling back to the live page on first open.
        const sourceVS = appViewState.historyPageViewState ?? appViewState.currentPageViewState;
        if (sourceVS) {
            pvs.viewportCenter.x = sourceVS.viewportCenter.x;
            pvs.viewportCenter.y = sourceVS.viewportCenter.y;
            pvs.viewportHeight = sourceVS.viewportHeight;
            pvs.viewportGeometry = [...sourceVS.viewportGeometry] as [number, number, number, number];
        }

        appViewState.historyPageViewState = pvs;
    }

    @action({ issuer: 'service' })
    setIntegrityError(state: ReplayPanelViewState, hasError: boolean) {
        state.hasIntegrityError = hasError;
    }

    @action({ issuer: 'service' })
    setIntegrityOp(state: ReplayPanelViewState, op: IntegrityOpState) {
        state.integrityOp = op;
    }

    @action({ issuer: 'service' })
    hideHistoryPage(appViewState: AppViewState) {
        appViewState.historyPageViewState = null;
    }

    @action({ issuer: 'service' })
    seekToPage(state: ReplayPanelViewState, markers: CommitMarker[], targetCommitId: string) {
        state.setCommitMarkers(markers);
        const markerIdx = markers.findIndex(m => m.id === targetCommitId);
        state.currentMarkerIdx = markerIdx >= 0 ? markerIdx : markers.length - 1;
    }
}

export const replayActions = new ReplayActions();
