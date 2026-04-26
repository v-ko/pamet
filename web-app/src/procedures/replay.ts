import { getLogger } from "fusion/logging";
import { pamet } from "@/app/facade";
import { appActions } from "@/actions/app";
import { replayActions } from "@/actions/replay";
import { ReplayService } from "@/services/ReplayService";

const log = getLogger("ReplayProcedures");

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
        appActions.updateSystemDialogState(appViewState, null);
    }
}

