import { InMemoryStore } from "fusion/storage/domain-store/InMemoryStore";
import { Delta, DeltaData, squashDeltas } from "fusion/model/Delta";
import { Change, ChangeType } from "fusion/model/Change";
import { getLogger } from "fusion/logging";
import { Entity, EntityData } from "fusion/model/Entity";
import { RestApiVcsAdapter } from "fusion/storage/repository/RestApiVcsAdapter";
import { RestApiAuthConfig } from "fusion/storage/rest-api/Auth";
import { replayActions } from "@/actions/replay";
import { pamet } from "@/app/facade";

let log = getLogger("ReplayService");

export const HISTORY_MODIFY_MSG = "You cannot modify history. You can only learn from it.";

/**
 * InMemoryStore subclass that can be locked to prevent external mutations.
 * When locked, insertOne/updateOne/removeOne throw unless the store is
 * temporarily unlocked by the ReplayService for animation operations.
 */
export class LockableStore extends InMemoryStore {
    private _locked = false;

    lock() { this._locked = true; }
    unlock() { this._locked = false; }
    get locked() { return this._locked; }

    insertOne(entity: Entity<EntityData>): Change {
        if (this._locked) {
            throw new Error(HISTORY_MODIFY_MSG);
        }
        return super.insertOne(entity);
    }

    updateOne(entity: Entity<EntityData>): Change {
        if (this._locked) {
            throw new Error(HISTORY_MODIFY_MSG);
        }
        return super.updateOne(entity);
    }

    removeOne(entity: Entity<EntityData>): Change {
        if (this._locked) {
            throw new Error(HISTORY_MODIFY_MSG);
        }
        return super.removeOne(entity);
    }
}

/** Metadata extracted per commit during the indexing phase. */
export interface CommitIndexEntry {
    id: string;
    timestamp: number;
    /** Size of the serialised delta_data (bytes). */
    deltaSize: number;
    /** Set of page IDs touched by this commit's delta. */
    touchedPageIds: Set<string>;
    /** Full delta data for this commit. */
    deltaData: DeltaData;
}

/** Result of the indexing phase for the entire project. */
export interface ProjectReplayIndex {
    /** Head commit ID at index time — used for staleness checks. */
    headCommitId: string;
    /** All commit entries in chronological order (full branch). */
    allCommits: CommitIndexEntry[];
    /** Sorted timestamps (all commits) for timeline density binning. */
    allTimestamps: number[];
}

/**
 * Manages the replay store and its connection to the replay PageViewState.
 *
 * The facade wires the store's onChanges to the shared reducer in readonly
 * mode. The store and mock AppViewState are owned by the facade.
 */
export class ReplayService {
    private _store: LockableStore;
    private _index: ProjectReplayIndex | null = null;
    private _vcsAdapter: RestApiVcsAdapter;
    private _storeStateAtCommitId: string | null = null;
    private _playbackTimer: ReturnType<typeof setTimeout> | null = null;
    private _baseUrl: string;
    private _pathPrefix: string;
    private _auth: RestApiAuthConfig;
    private _integrityAbort: AbortController | null = null;

    /** Expose the project index (null if not yet built). */
    get index(): ProjectReplayIndex | null { return this._index; }

    constructor(
        store: LockableStore,
        pathPrefix: string,
        localBranchName: string,
        baseUrl: string,
        auth: RestApiAuthConfig,
    ) {
        this._store = store;
        this._baseUrl = baseUrl;
        this._pathPrefix = pathPrefix;
        this._auth = auth;
        this._vcsAdapter = new RestApiVcsAdapter(pathPrefix, localBranchName, baseUrl, auth);
    }


    /**
     * Fetch all commits from the backend in batches and build the project
     * replay index.  Returns the index and calls `onProgress` between
     * batches so the caller can update UI and yield to the event loop.
     *
     * To keep entity→page resolution correct for UPDATEs/DELETEs
     * (where `parent_id` may not appear in the delta), we maintain a
     * local map of entityId→pageId, updated as we process CREATEs.
     */
    async buildProjectIndex(
        onProgress?: (processed: number, total: number | null) => void,
    ): Promise<ProjectReplayIndex> {
        const batchSize = 200;

        const commitGraph = await this._vcsAdapter.getCommitGraph();
        const branchCommits = commitGraph.branchCommits(this._vcsAdapter.localBranchName);
        const commitIds = branchCommits.map(c => c.id);
        const total = commitIds.length;
        const headCommitId = commitIds.length > 0 ? commitIds[commitIds.length - 1] : "";

        const entityPageMap = new Map<string, string>();
        const allEntries: CommitIndexEntry[] = [];

        for (let i = 0; i < commitIds.length; i += batchSize) {
            const batchIds = commitIds.slice(i, i + batchSize);
            const commits = await this._vcsAdapter.getCommits(batchIds);

            for (const commit of commits) {
                const deltaData = commit.deltaData;
                const deltaSize = JSON.stringify(deltaData).length;
                const touchedPageIds = this._extractPageIds(deltaData, entityPageMap);

                allEntries.push({
                    id: commit.id,
                    timestamp: commit.timestamp,
                    deltaSize,
                    touchedPageIds,
                    deltaData,
                });
            }

            onProgress?.(allEntries.length, total);

            // Yield to the event loop so UI can update
            await new Promise(r => setTimeout(r, 0));
        }

        const allTimestamps = allEntries.map(e => e.timestamp);

        const index: ProjectReplayIndex = {
            headCommitId,
            allCommits: allEntries,
            allTimestamps,
        };

        log.info(
            `Project index built: ${allEntries.length} total commits`
        );

        this._index = index;
        return index;
    }

    /**
     * Extract the set of page IDs touched by a delta's changes.
     *
     * For CREATEs: read `parent_id` from the forward component and
     * record it in the entity→page map.
     * For UPDATEs: if `parent_id` is in the forward component use that
     * (it's being re-parented), otherwise look up the entity→page map.
     * For DELETEs: look up from the reverse component or the map.
     */
    private _extractPageIds(
        deltaData: DeltaData,
        entityPageMap: Map<string, string>,
    ): Set<string> {
        const pageIds = new Set<string>();

        for (const changeData of Object.values(deltaData)) {
            const change = new Change(changeData);
            const entityId = change.entityId;
            const type = change.type();

            if (type === ChangeType.CREATE) {
                const parentId = change.forwardComponent.parent_id as string | undefined;
                if (parentId) {
                    entityPageMap.set(entityId, parentId);
                    pageIds.add(parentId);
                }
            } else if (type === ChangeType.UPDATE) {
                // Check if parent_id itself changed
                const newParentId = change.forwardComponent.parent_id as string | undefined;
                const oldParentId = change.reverseComponent.parent_id as string | undefined;
                if (newParentId) {
                    entityPageMap.set(entityId, newParentId);
                    pageIds.add(newParentId);
                }
                if (oldParentId) {
                    pageIds.add(oldParentId);
                }
                // Also include the page the entity currently belongs to
                const knownPageId = entityPageMap.get(entityId);
                if (knownPageId) {
                    pageIds.add(knownPageId);
                }
            } else if (type === ChangeType.DELETE) {
                const parentId = change.reverseComponent.parent_id as string | undefined;
                if (parentId) {
                    pageIds.add(parentId);
                } else {
                    const knownPageId = entityPageMap.get(entityId);
                    if (knownPageId) {
                        pageIds.add(knownPageId);
                    }
                }
                entityPageMap.delete(entityId);
            }
        }

        return pageIds;
    }

    clear() {
        this.stopPlayback();
        this._store.unlock();
        this._store.clear();
        this._index = null;
        this._storeStateAtCommitId = null;
    }

    // ── Playback engine ─────────────────────────────────────────

    /**
     * Set the store state to match the snapshot at the given commit,
     * optimized for the given page.
     *
     * Adjacent-commit optimization: if the store is one global step
     * behind or ahead, applies a single delta instead of full replay.
     *
     * Page-aware replay optimization: during full replay, deltas for
     * commits not relevant to the page are accumulated and squashed
     * together, only applied when a page-relevant commit is reached.
     */
    seekSnapshot(targetCommitId: string, pageId: string): void {
        const index = this._index;
        if (!index) {
            throw new Error("Cannot seekSnapshot: no index built");
        }

        // Already at the target commit
        if (this._storeStateAtCommitId === targetCommitId) {
            return;
        }

        const ac = index.allCommits;
        const targetIdx = ac.findIndex(c => c.id === targetCommitId);
        if (targetIdx === -1) {
            throw new Error(`Commit ${targetCommitId} not found in index`);
        }

        // Optimization: store is one commit behind (forward single-delta apply)
        if (targetIdx > 0 && this._storeStateAtCommitId === ac[targetIdx - 1].id) {
            this._store.unlock();
            this._store.applyDelta(new Delta(ac[targetIdx].deltaData), undefined, true);
            this._store.lock();
            this._storeStateAtCommitId = targetCommitId;
            return;
        }

        // Optimization: store is one commit ahead (reverse single-delta apply)
        if (targetIdx < ac.length - 1 && this._storeStateAtCommitId === ac[targetIdx + 1].id) {
            this._store.unlock();
            const reversedDelta = new Delta(ac[targetIdx + 1].deltaData).reversed();
            this._store.applyDelta(reversedDelta, undefined, true);
            this._store.lock();
            this._storeStateAtCommitId = targetCommitId;
            return;
        }

        // Full replay from the beginning — squash all deltas and apply once.
        this._store.unlock();
        this._store.clear();

        const allDeltas = ac.slice(0, targetIdx + 1).map(c => c.deltaData);
        let squashed: DeltaData;
        if (allDeltas.length === 1) {
            squashed = allDeltas[0];
        } else {
            squashed = squashDeltas(allDeltas).data;
        }
        this._store.applyDelta(new Delta(squashed), undefined, true);

        this._store.lock();
        this._storeStateAtCommitId = targetCommitId;
    }

    startPlayback(
        currentPageId: string,
        initialCommitId: string,
        endCommitId: string,
        direction: 'forward' | 'reverse',
        onTick?: (commitId: string) => void,
        intervalMs: number = 300,
    ): void {
        this.stopPlayback();
        const index = this._index;
        if (!index) return;

        const ac = index.allCommits;

        // Get page-relevant global indices
        const pageRelevantIndices = ReplayService.getPageRelevantIndices(index, currentPageId);
        if (pageRelevantIndices.length === 0) return;

        // Find initial and end positions in the global list
        const initialGlobalIdx = ac.findIndex(c => c.id === initialCommitId);
        const endGlobalIdx = ac.findIndex(c => c.id === endCommitId);
        if (initialGlobalIdx === -1 || endGlobalIdx === -1) return;

        // Filter page-relevant indices to those within the playback range
        let relevantInRange: number[];
        if (direction === 'forward') {
            relevantInRange = pageRelevantIndices.filter(
                i => i >= initialGlobalIdx && i <= endGlobalIdx
            );
        } else {
            relevantInRange = pageRelevantIndices
                .filter(i => i >= endGlobalIdx && i <= initialGlobalIdx)
                .reverse();
        }
        if (relevantInRange.length === 0) return;

        // Set initial snapshot
        this.seekSnapshot(ac[relevantInRange[0]].id, currentPageId);
        onTick?.(ac[relevantInRange[0]].id);

        let currentStep = 0;

        const tick = () => {
            currentStep++;
            if (currentStep >= relevantInRange.length) {
                this.stopPlayback();
                const replayVS = pamet.appViewState.replayPanelVS;
                if (replayVS) replayActions.setReplayPlaying(replayVS, false);
                // Forward playback ends at the latest commit — return to live view
                if (direction === 'forward') {
                    replayActions.hideHistoryPage(pamet.appViewState);
                    if (replayVS) replayVS.currentMarkerIdx = -1;
                }
                return;
            }
            this.seekSnapshot(ac[relevantInRange[currentStep]].id, currentPageId);
            onTick?.(ac[relevantInRange[currentStep]].id);
            this._playbackTimer = setTimeout(tick, intervalMs);
        };
        this._playbackTimer = setTimeout(tick, intervalMs);
    }
    /**
     * Get the indices into allCommits that are relevant to a specific page.
     * Returns a sorted array of global indices where the commit touches pageId.
     */
    static getPageRelevantIndices(index: ProjectReplayIndex, pageId: string): number[] {
        const indices: number[] = [];
        for (let i = 0; i < index.allCommits.length; i++) {
            if (index.allCommits[i].touchedPageIds.has(pageId)) {
                indices.push(i);
            }
        }
        return indices;
    }

    /** Stop any running playback timer. */
    stopPlayback(): void {
        if (this._playbackTimer !== null) {
            clearTimeout(this._playbackTimer);
            this._playbackTimer = null;
        }
    }

    /** Return the commit ID closest to the given timestamp, considering only page-relevant commits. */
    static commitIdClosestToTimestamp(index: ProjectReplayIndex, pageId: string, timestamp: number): string | null {
        const pri = ReplayService.getPageRelevantIndices(index, pageId);
        if (pri.length === 0) return null;

        let bestIdx = 0;
        let bestDist = Math.abs(index.allCommits[pri[0]].timestamp - timestamp);
        for (let i = 1; i < pri.length; i++) {
            const dist = Math.abs(index.allCommits[pri[i]].timestamp - timestamp);
            if (dist < bestDist) {
                bestDist = dist;
                bestIdx = i;
            }
        }

        return index.allCommits[pri[bestIdx]].id;
    }

    // -----------------------------------------------------------------------
    // VCS Integrity Operations
    // -----------------------------------------------------------------------

    /**
     * Run an integrity operation via SSE. Calls onProgress for each event,
     * onDone when completed. Returns an abort function.
     */
    private _runIntegritySSE(
        endpoint: string,
        onProgress: (data: any) => void,
        onDone: (data: any) => void,
        onError: (err: string) => void,
    ): () => void {
        const abort = new AbortController();
        this._integrityAbort = abort;

        const url = `${this._baseUrl}${this._pathPrefix}/${endpoint}`;
        const headers: Record<string, string> = {
            Authorization: `Bearer ${this._auth.token}`,
        };

        fetch(url, { method: "POST", headers, signal: abort.signal })
            .then(async (response) => {
                if (!response.ok) {
                    onError(`HTTP ${response.status}: ${response.statusText}`);
                    return;
                }
                const reader = response.body?.getReader();
                if (!reader) {
                    onError("No response body");
                    return;
                }
                const decoder = new TextDecoder();
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    // Parse SSE lines
                    const lines = buffer.split("\n");
                    buffer = lines.pop() || "";
                    for (const line of lines) {
                        if (line.startsWith("data: ")) {
                            const payload = JSON.parse(line.slice(6));
                            if (payload.type === "done") {
                                onDone(payload);
                            } else {
                                onProgress(payload);
                            }
                        }
                    }
                }
            })
            .catch((err) => {
                if (err.name !== "AbortError") {
                    onError(String(err));
                }
            })
            .finally(() => {
                this._integrityAbort = null;
            });

        return () => abort.abort();
    }

    /** Check all history for mismatches (linear replay). */
    checkAllHistory(
        onProgress: (data: any) => void,
        onDone: (data: any) => void,
        onError: (err: string) => void,
    ): () => void {
        return this._runIntegritySSE("check-all", onProgress, onDone, onError);
    }

    /** Repair all mismatched hashes (linear replay + fix). */
    repairHashes(
        onProgress: (data: any) => void,
        onDone: (data: any) => void,
        onError: (err: string) => void,
    ): () => void {
        return this._runIntegritySSE("repair-hashes", onProgress, onDone, onError);
    }

    /** Cancel any running integrity operation. */
    cancelIntegrityOp(): void {
        this._integrityAbort?.abort();
        this._integrityAbort = null;
    }
}
