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
const COMMIT_SAFETY_TIMEOUT_MS = 10000;

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
 * Does NOT own the store. Does NOT touch the view model.
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
    private _expectedDelta: Delta = new Delta({});

    private _commitInFlight = false;
    private _flushTimer: ReturnType<typeof setTimeout> | null = null;
    private _commitSafetyTimer: ReturnType<typeof setTimeout> | null = null;

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

        this._beforeUnloadHandler = (e: BeforeUnloadEvent) => {
            if (!this._unstagedChanges.isEmpty() ||
                !this._stagedChanges.isEmpty() ||
                !this._expectedDelta.isEmpty()) {
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
        log.info('OPSS initialized successfully');
        return syncDelta;
    }

    /**
     * Record a delta for later commit. Skips remote-origin deltas.
     * Designed to be called directly from store.onChanges.
     */
    trackDelta(delta: Delta, origin?: string) {
        if (origin === 'remote') {
            return;
        }
        if (!delta.isEmpty()) {
            this._unstagedChanges.mergeWithPriority(delta);
        }
    }

    /**
     * Stage accumulated uncommitted changes for commit.
     * The actual network commit is debounced and serialized (one in-flight at a time).
     * Returns true if data was staged, false if there was nothing to stage.
     */
    saveUncommittedChanges(): boolean {
        if (this._unstagedChanges.isEmpty()) {
            return false;
        }

        log.info('Staging uncommitted delta');

        // Move uncommitted → staged. This replaces _uncommittedDelta with a new
        // object so that undo references (which hold the old object) remain stable.
        this._stagedChanges.mergeWithPriority(this._unstagedChanges);
        this._unstagedChanges = new Delta({});

        this._scheduleFlush();
        return true;
    }

    private _scheduleFlush() {
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
        if (this._stagedChanges.isEmpty()) {
            return;
        }
        if (this._commitInFlight) {
            // Will be retried when the current commit's repo-update arrives
            return;
        }

        this._commitInFlight = true;
        const delta = this._stagedChanges;
        this._stagedChanges = new Delta({});
        this._expectedDelta.mergeWithPriority(delta);

        appActions.setSaveStatus(pamet.appViewState, 'saving');

        this._storageService.commit(this._projectId, delta.data, 'Auto-commit')
            .then((result) => {
                const appliedDeltaData = result.commit.delta_data;
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
            })
            .catch((error) => {
                log.error('Auto-commit failed. Returning delta to staged.', {
                    error,
                    projectId: this._projectId,
                    delta: delta.data,
                });

                // Remove the failed delta from expectedDelta so reconciliation
                // doesn't try to reverse changes that were never applied remotely.
                const reversedFailed = delta.reversed();
                this._expectedDelta.mergeWithPriority(reversedFailed);

                // Put the failed changes back into staged so the next flush retries them.
                delta.mergeWithPriority(this._stagedChanges);
                this._stagedChanges = delta;

                this._commitInFlight = false;
                appActions.setSaveStatus(pamet.appViewState, 'error');

                // Re-schedule flush for retry
                this._scheduleFlush();
            });

        // Safety timeout: if we never receive a repoUpdate, unblock commits
        this._commitSafetyTimer = setTimeout(() => {
            if (this._commitInFlight) {
                log.warning('Commit safety timeout reached — clearing in-flight flag');
                this._commitInFlight = false;
                this._flushStaged();
            }
        }, COMMIT_SAFETY_TIMEOUT_MS);
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
        log.info('Received repo update', repoUpdate);

        try {
            const remoteGraph = CommitGraph.fromData(repoUpdate.commitGraph);
            const upsertedCommits = repoUpdate.upsertedCommits.map(data => new Commit(data));

            const repoSyncDelta = computeRepoSyncDelta(
                this._localCommitGraph, remoteGraph, upsertedCommits, this._currentBranch
            );

            if (!repoSyncDelta) {
                log.info('No repo sync changes needed');
                this._onCommitSettled();
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

        this._onCommitSettled();
    }

    private _onCommitSettled() {
        this._commitInFlight = false;
        if (this._commitSafetyTimer !== null) {
            clearTimeout(this._commitSafetyTimer);
            this._commitSafetyTimer = null;
        }

        // If there's more staged work, flush it now
        if (!this._stagedChanges.isEmpty()) {
            this._flushStaged();
        } else if (this._unstagedChanges.isEmpty()) {
            appActions.setSaveStatus(pamet.appViewState, 'saved');
        }
    }
}
