import { getLogger } from "sivkit/logging";
import { Store } from "sivkit/storage/domain-store/BaseStore";
import { Delta } from "sivkit/model/Delta";
import { CommitGraph } from "sivkit/storage/version-control/CommitGraph";
import { Commit } from "sivkit/storage/version-control/Commit";
import { computeRepoSyncDelta } from "sivkit/storage/management/sync-utils";
import type { RepoUpdateData } from "sivkit/storage/repository/Repository";
import type { StorageServiceProxy } from "sivkit/storage/management/StorageServiceProxy";
import { action } from "sivkit/registries/Action";
import { appActions } from "@/actions/app";
import { pamet } from "@/app/facade";

let log = getLogger('OptimisticProjectSyncService');

const FLUSH_DEBOUNCE_MS = 100;
const CLOSE_TIMEOUT_MS = 5000;

export type CloseOutcome = 'completed' | 'failed' | 'timed out';

/**
 * Handles the optimistic-commit + reconciliation cycle for a single project.
 *
 * Responsibilities:
 * - Accumulates uncommitted changes from the store
 * - Sends commits to the authority (StorageService) asynchronously
 * - Tracks what was sent (expectedDelta)
 * - Receives authority updates (via Channel/BroadcastChannel)
 * - Reconciles: reverses the expected delta, applies the authority's actual delta
 *   back into the store
 *
 * Commits are serialized (only one in-flight at a time) and debounced to
 * avoid races where a repo-update reverses not-yet-committed changes.
 *
 * Does NOT own the store. Reports save status through app actions.
 * The store's onChange callback is the view model's concern.
 */
export class OptimisticProjectSyncService {
    private _store: Store;
    private _storageService: StorageServiceProxy;
    private _projectId: string;

    private _localCommitGraph: CommitGraph;
    private _currentBranch: string;
    private _unstagedChanges: Delta = new Delta({});
    private _stagedChanges: Delta = new Delta({});
    private _stagedActionNames: string[] = [];
    private _expectedDelta: Delta = new Delta({});

    private _requestError: string | null = null;
    private _pendingCommit: Promise<boolean> | null = null;
    private _closing = false;
    private _disposed = false;
    private _flushTimer: ReturnType<typeof setTimeout> | null = null;

    private _beforeUnloadHandler: ((e: BeforeUnloadEvent) => void) | null = null;

    constructor(
        store: Store,
        storageService: StorageServiceProxy,
        projectId: string,
        currentBranch: string,
    ) {
        this._store = store;
        this._storageService = storageService;
        this._projectId = projectId;
        this._currentBranch = currentBranch;
        this._localCommitGraph = new CommitGraph();
        appActions.setSaveError(pamet.appViewState, null);

        this._beforeUnloadHandler = (e: BeforeUnloadEvent) => {
            if (!this._unstagedChanges.isEmpty() ||
                !this._stagedChanges.isEmpty() ||
                !this._expectedDelta.isEmpty() || this._pendingCommit || this._hasSaveErrors()) {
                e.preventDefault();
            }
        };
        window.addEventListener('beforeunload', this._beforeUnloadHandler);
    }

    get uncommittedDelta(): Delta {
        return this._unstagedChanges;
    }

    /**
     * Hydrate from the storage service. Pulls the remote commit graph and
     * applies the initial delta to the store.
     * Returns the delta that was applied (for callers that need it, e.g. to
     * initialize the view model).
     */
    async initialize(): Promise<Delta | null> {
        const remoteGraphData = await this._storageService.getCommitGraph(this._projectId);
        const remoteGraph = CommitGraph.fromData(remoteGraphData);

        const emptyLocalGraph = new CommitGraph();
        emptyLocalGraph.createBranch(this._currentBranch);

        const allCommits = remoteGraph.commits();
        const allCommitIds = allCommits.map(c => c.id);
        let upsertedCommits: Commit[] = [];

        if (allCommitIds.length > 0) {
            const commitDataArray = await this._storageService.getCommits(this._projectId, allCommitIds);
            upsertedCommits = commitDataArray.map(data => new Commit(data));
        }

        const syncDelta = computeRepoSyncDelta(emptyLocalGraph, remoteGraph, upsertedCommits, this._currentBranch);
        if (syncDelta) {
            this._store.applyDelta(syncDelta, 'remote');
        }

        this._localCommitGraph = remoteGraph;
        this._updateSaveStatus();
        log.info('OPSS initialized successfully');
        return syncDelta;
    }

    /**
     * Record a delta for later commit. Skips remote-origin deltas.
     * Designed to be called directly from store.onChanges.
     */
    trackDelta(delta: Delta, origin?: string) {
        if (this._disposed || this._closing || origin === 'remote') {
            return;
        }
        if (!delta.isEmpty()) {
            this._unstagedChanges.mergeWithPriority(delta);
            this._updateSaveStatus();
        }
    }

    /**
     * Stage accumulated uncommitted changes for commit.
     * The actual network commit is debounced and serialized (one in-flight at a time).
     * Returns true if data was staged, false if there was nothing to stage.
     */
    saveUncommittedChanges(actionName?: string): boolean {
        if (this._disposed || this._unstagedChanges.isEmpty()) {
            return false;
        }

        log.info('Staging uncommitted delta');

        // Move uncommitted → staged. This replaces _uncommittedDelta with a new
        // object so that undo references (which hold the old object) remain stable.
        this._stagedChanges.mergeWithPriority(this._unstagedChanges);
        this._unstagedChanges = new Delta({});
        if (actionName) this._stagedActionNames.push(actionName);

        this._scheduleFlush();
        this._updateSaveStatus();
        return true;
    }

    private _scheduleFlush() {
        if (this._closing) return;
        // Reset the debounce timer on each call (trailing-edge debounce)
        if (this._flushTimer !== null) {
            clearTimeout(this._flushTimer);
        }
        this._flushTimer = setTimeout(() => {
            this._flushTimer = null;
            this._flushStaged();
        }, FLUSH_DEBOUNCE_MS);
    }

    private _flushStaged() {
        if (this._disposed || this._stagedChanges.isEmpty()) {
            return;
        }
        if (this._pendingCommit) {
            // The request completion sends any staged work next.
            return;
        }

        const delta = this._stagedChanges;
        this._stagedChanges = new Delta({});
        const actionNames = this._stagedActionNames;
        this._stagedActionNames = [];
        this._expectedDelta.mergeWithPriority(delta);
        const expected = this._expectedDelta;

        const pendingCommit = this._storageService.commit(this._projectId, delta.data, actionNames.join(', ') || 'Auto-commit')
            .then((result) => {
                const appliedDeltaData = result.commit.delta_data;
                const failed = result.domainSaveResult?.ok === false;
                if (failed && !result.domainSaveResult?.reported && !this._disposed) {
                    this._recordRequestError(result.domainSaveResult?.message ?? 'Save failed');
                }
                const unappliedDelta = delta.copy();
                unappliedDelta.mergeWithPriority(new Delta(appliedDeltaData).reversed());
                if (!unappliedDelta.isEmpty()) {
                    log.warning('Auto-commit skipped conflicting local changes.', {
                        projectId: this._projectId,
                        unappliedDelta: unappliedDelta.data,
                        appliedDelta: appliedDeltaData,
                        commit: result.commit,
                    });
                }
                return !failed;
            })
            .catch((error) => {
                if (this._disposed) {
                    log.error('Save failed after the project was closed', { error, delta: delta.data });
                    return false;
                }
                // Removal discards local work; other failures remain visible.
                if (error?.name === 'ProjectStorageLifecycleError' &&
                    !pamet.trackedProjects().some(project => project.id === this._projectId)) {
                    this._stopForRemoval();
                    return false;
                }
                log.error('Save failed; the delta will not be resent.', {
                    error,
                    projectId: this._projectId,
                    delta: delta.data,
                });

                // A repo update replaces this accumulator after reconciliation.
                if (this._expectedDelta === expected) {
                    this._expectedDelta.mergeWithPriority(delta.reversed());
                }
                this._recordRequestError(error instanceof Error ? error.message : String(error));
                return false;
            })
            .finally(() => {
                this._pendingCommit = null;
                if (!this._disposed && !this._closing) {
                    this._flushStaged();
                    this._updateSaveStatus();
                }
            });
        this._pendingCommit = pendingCommit;
        this._updateSaveStatus();

    }

    private _recordRequestError(message: string) {
        // An unrelated successful edit cannot recover a rejected/unknown save.
        this._requestError = message;
        appActions.setSaveError(pamet.appViewState, message);
    }

    private _hasSaveErrors(): boolean {
        const fs = pamet.projectStorageState(this._projectId)?.filesystem;
        return this._requestError !== null || Object.keys(fs?.errors ?? {}).length > 0
            || pamet.appViewState.storageState.backendConnected === false;
    }

    private _updateSaveStatus() {
        if (this._disposed) return;
        const status = this._requestError ? 'error'
            : this._pendingCommit ? 'saving'
            : !this._unstagedChanges.isEmpty() || !this._stagedChanges.isEmpty() ? 'unsaved'
            : 'saved';
        appActions.setSaveStatus(pamet.appViewState, status);
    }

    /**
     * Prepare to close: stop taking edits, send the pending save and wait for
     * it. The timers and the beforeunload listener are disposed even when the
     * save fails or times out; the unsaved changes are then logged.
     */
    async flushAndDispose(timeoutMs = CLOSE_TIMEOUT_MS): Promise<CloseOutcome> {
        this.saveUncommittedChanges('Close');
        this._closing = true;
        if (this._flushTimer !== null) clearTimeout(this._flushTimer);
        this._flushTimer = null;

        let timeout: ReturnType<typeof setTimeout> | undefined;
        const timedOut = new Promise<CloseOutcome>(resolve => {
            timeout = setTimeout(() => resolve('timed out'), timeoutMs);
        });
        const outcome = await Promise.race([this._drain(), timedOut]);
        clearTimeout(timeout);

        if (outcome !== 'completed') {
            log.error(`Closing project ${this._projectId}: save ${outcome}`, {
                unsent: this._stagedChanges.data,
                requestPending: !!this._pendingCommit,
            });
        }
        // Closing reports its final outcome before disposing status updates.
        appActions.setSaveStatus(pamet.appViewState, outcome === 'completed' ? 'saved' : 'error');
        this._dispose();
        return outcome;
    }

    private async _drain(): Promise<CloseOutcome> {
        while (this._pendingCommit || !this._stagedChanges.isEmpty()) {
            if (this._disposed) return 'timed out';
            if (this._pendingCommit) {
                if (!await this._pendingCommit) return 'failed';
                continue;
            }
            // Closing doesn't wait for the repo update, only for the request
            this._flushStaged();
        }
        return this._hasSaveErrors() ? 'failed' : 'completed';
    }

    private _dispose() {
        this._disposed = true;
        if (this._flushTimer !== null) clearTimeout(this._flushTimer);
        if (this._beforeUnloadHandler) window.removeEventListener('beforeunload', this._beforeUnloadHandler);
        this._flushTimer = null;
        this._beforeUnloadHandler = null;
    }

    private _stopForRemoval() {
        this._dispose();
        this._pendingCommit = null;
        this._expectedDelta = new Delta({});
        this._stagedChanges = new Delta({});
        this._unstagedChanges = new Delta({});
        this._stagedActionNames = [];
        log.info('Discarding pending save for removed project', this._projectId);
    }

    /**
     * Receive an update from the authority (via BroadcastChannel).
     * Reconciles optimistic local state with the canonical remote state.
     *
     * Decorated as a service action so MobX batching applies to the
     * store.onChange → view model reducer calls triggered by applyDelta.
     */
    @action({ issuer: 'service' })
    receiveRepoUpdate(repoUpdate: RepoUpdateData) {
        // While closing, the store is about to be dropped
        if (this._disposed || this._closing) return;
        log.info('Received repo update', repoUpdate);

        try {
            const remoteGraph = CommitGraph.fromData(repoUpdate.commitGraph);
            const upsertedCommits = repoUpdate.upsertedCommits.map(data => new Commit(data));

            const repoSyncDelta = computeRepoSyncDelta(
                this._localCommitGraph, remoteGraph, upsertedCommits, this._currentBranch
            );

            if (!repoSyncDelta) {
                log.info('No repo sync changes needed');
                return;
            }

            // Reconcile: reverse what we expected, apply what actually happened
            // S2 + (reversed(C) + C') = S2'
            let reversedExpectedDelta = this._expectedDelta.reversed();
            this._expectedDelta = new Delta({});

            reversedExpectedDelta.mergeWithPriority(repoSyncDelta);
            let finalDelta = reversedExpectedDelta;

            this._store.applyDelta(finalDelta, 'remote');

            this._localCommitGraph = remoteGraph;
            log.info('Successfully applied repo update');
        } catch (e) {
            log.error('Error applying repo update:', e);
            alert('Critical error (check the console). Please reload the page');
        }

    }
}
