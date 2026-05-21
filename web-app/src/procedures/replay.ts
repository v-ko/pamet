import { getLogger } from "fusion/logging";
import { pamet } from "@/app/facade";
import { appActions } from "@/actions/app";
import { replayActions } from "@/actions/replay";
import { ReplayService } from "@/services/ReplayService";
import { PametRoute } from "@/services/routing/PametRoute";
import { ReplayPanelViewState } from "@/views/replay/ReplayViewState";

const log = getLogger("ReplayProcedures");

/** Check backend status for integrity errors and flag the replay panel. */
export async function checkIntegrityStatus(): Promise<void> {
    const baseUrl = (window as any).PAMET_DESKTOP_API_BASE_URL;
    const token = (window as any).PAMET_DESKTOP_ACCESS_TOKEN;
    if (!baseUrl || !token) return;

    const vs = pamet.appViewState.replayPanelVS;
    if (!vs) return;

    try {
        const resp = await fetch(`${baseUrl}/status`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        console.log("[INTEGRITY] /status response:", resp.status);
        if (!resp.ok) {
            console.log("[INTEGRITY] /status not OK");
            return;
        }
        const status = await resp.json();
        const changeHistoryErrors = status?.errors?.change_history;
        console.log("[INTEGRITY] change_history errors:", changeHistoryErrors);
        let hasIntegrity = false;
        if (changeHistoryErrors && Object.keys(changeHistoryErrors).length > 0) {
            hasIntegrity = Object.values(changeHistoryErrors).some(
                (msg: any) => typeof msg === "string" && msg.includes("hash mismatch")
            );
        }
        console.log("[INTEGRITY] hasIntegrity:", hasIntegrity, "vs:", vs);
        replayActions.setIntegrityError(vs, hasIntegrity);
        console.log("[INTEGRITY] vs.hasIntegrityError set to:", vs.hasIntegrityError);
    } catch (e) {
        console.error("[INTEGRITY] checkIntegrityStatus failed:", e);
    }
}

/** Start a long-running integrity operation (check or repair) with progress tracking. */
export function startIntegrityOp(
    state: ReplayPanelViewState,
    method: "checkAllHistory" | "repairHashes",
) {
    const svc = pamet.replayService;
    replayActions.setIntegrityOp(state, { status: "running", progressIndex: 0, progressTotal: 0, resultSummary: null });

    svc[method](
        (data) => {
            replayActions.setIntegrityOp(state, {
                ...state.integrityOp,
                progressIndex: data.index ?? data.step ?? state.integrityOp.progressIndex,
                progressTotal: data.total ?? data.totalSteps ?? state.integrityOp.progressTotal,
            });
        },
        (data) => {
            let summary: string;
            if (data.fixed !== undefined) {
                summary = `Repaired ${data.fixed} of ${data.total} commits.`;
                if (data.recovered) {
                    summary += " Service recovered.";
                    void checkIntegrityStatus().then(() => buildReplayIndex());
                }
            } else if (data.mismatches !== undefined) {
                summary = `Checked ${data.total} commits: ${data.mismatches} mismatches found.`;
            } else {
                summary = "Done.";
            }
            if (data.log_path) {
                alert(`${summary}\n\nOpening diagnostics log:\n${data.log_path}`);
            }
            replayActions.setIntegrityOp(state, { status: "done", progressIndex: 0, progressTotal: 0, resultSummary: summary });
        },
        (err) => {
            replayActions.setIntegrityOp(state, { status: "error", progressIndex: 0, progressTotal: 0, resultSummary: `Error: ${err}` });
        },
    );
}

/** Guard against concurrent index builds (e.g. rapid project switches). */
let _buildGeneration = 0;

export async function buildReplayIndex(): Promise<void> {
    const replayViewState = pamet.appViewState.replayPanelVS;
    if (!replayViewState) {
        log.error("Cannot build replay index: replay panel not open");
        return;
    }

    const projectId = pamet.appViewState.currentProjectId;
    if (!projectId) {
        log.error("Cannot build replay index: no current project");
        return;
    }

    const currentPageId = pamet.appViewState.currentPageId;

    const service = pamet.replayService;
    const appViewState = pamet.appViewState;

    // Clear old replay state (also stops any running playback)
    service.clear();

    const generation = ++_buildGeneration;

    appActions.updateSystemDialogState(appViewState, {
        title: "Building replay index\u2026",
        taskDescription: "Fetching commits\u2026",
        taskProgress: -1,  // indeterminate
    });

    try {
        const index = await service.buildProjectIndex(
            (processed, total) => {
                const description = total !== null
                    ? `Processed ${processed} / ${total} commits`
                    : `Processed ${processed} commits\u2026`;
                const progress = total !== null
                    ? (processed / total) * 100
                    : -1;
                appActions.updateSystemDialogState(appViewState, {
                    taskDescription: description,
                    taskProgress: progress,
                });
            },
        );

        // A newer build was started while we were fetching — discard results
        if (generation !== _buildGeneration) {
            log.info("Discarding stale index build (project changed during fetch)");
            return;
        }

        // Build page-relevant commit markers for the view state
        const markers = currentPageId
            ? ReplayService.getPageRelevantIndices(index, currentPageId)
                .map(i => ({ id: index.allCommits[i].id, timestamp: index.allCommits[i].timestamp }))
            : [];

        replayActions.updatePanelFromReplayIndex(replayViewState, projectId, markers);

        log.info(`Replay index ready: ${index.allCommits.length} commits, ${markers.length} page-relevant`);
    } catch (err) {
        log.error("Failed to build replay index", err);
    } finally {
        if (appViewState.loadingDialogState !== null) {
            appActions.updateSystemDialogState(appViewState, null);
        }
        console.log("[INTEGRITY] buildReplayIndex finally: calling checkIntegrityStatus");
        void checkIntegrityStatus();
    }
}

/**
 * Navigate the replay view to a different page, seeking to the commit
 * closest to the current replay timestamp. Falls back to the latest
 * available version if no exact match exists.
 *
 * If the target page has no history at all, closes the replay and
 * navigates to the live page.
 */
export async function navigateReplayToPage(targetPageId: string): Promise<void> {
    const appVS = pamet.appViewState;
    const replayVS = appVS.replayPanelVS;
    const service = pamet.replayService;
    const index = service.index;

    if (!replayVS || !index) {
        // Replay not active or index not built — just close and navigate live
        replayActions.hideHistoryPage(appVS);
        replayActions.closeReplay(appVS);
        await pamet.navigateTo(new PametRoute({
            userId: appVS.userId,
            projectId: appVS.currentProjectId ?? undefined,
            pageId: targetPageId,
        }));
        return;
    }

    // Get the current replay timestamp from the active marker
    const currentIdx = replayVS.currentMarkerIdx;
    const currentTimestamp = currentIdx >= 0 && currentIdx < replayVS.commitMarkers.length
        ? replayVS.commitMarkers[currentIdx].timestamp
        : replayVS.commitMarkers[replayVS.commitMarkers.length - 1]?.timestamp ?? Date.now();

    // Check if the target page has any history
    const targetCommitId = ReplayService.commitIdClosestToTimestamp(index, targetPageId, currentTimestamp);

    if (!targetCommitId) {
        // No history for target page — close replay overlay and navigate live
        log.info(`No history for page ${targetPageId}, closing replay and navigating live`);
        service.stopPlayback();
        replayActions.hideHistoryPage(appVS);
        replayActions.closeReplay(appVS);
        await pamet.navigateTo(new PametRoute({
            userId: appVS.userId,
            projectId: appVS.currentProjectId ?? undefined,
            pageId: targetPageId,
        }));
        return;
    }

    // Stop any running playback
    service.stopPlayback();
    replayActions.setReplayPlaying(replayVS, false);

    // Hide the old history page BEFORE seeking, so the reducer doesn't
    // try to apply deltas to a stale page view state.
    replayActions.hideHistoryPage(appVS);

    // Navigate the live view to the target page
    await pamet.navigateTo(new PametRoute({
        userId: appVS.userId,
        projectId: appVS.currentProjectId ?? undefined,
        pageId: targetPageId,
    }));

    // Re-filter markers for the target page
    const markers = ReplayService.getPageRelevantIndices(index, targetPageId)
        .map(i => ({ id: index.allCommits[i].id, timestamp: index.allCommits[i].timestamp }));

    replayActions.seekToPage(replayVS, markers, targetCommitId);

    // Seek the replay store (reducer is a no-op since historyPVS is null)
    // then create a fresh history page view state from the resulting store.
    service.seekSnapshot(targetCommitId, targetPageId);
    replayActions.showHistoryPage(appVS, pamet.historyStore, targetPageId);
}

