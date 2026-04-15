import { getLogger } from "fusion/logging";
import { Store } from "fusion/storage/domain-store/BaseStore";
import { Delta } from "fusion/model/Delta";
import { CommitGraph } from "fusion/storage/version-control/CommitGraph";
import { Commit } from "fusion/storage/version-control/Commit";
import { computeRepoSyncDelta } from "fusion/storage/management/sync-utils";
import type { RepoUpdateData } from "fusion/storage/repository/Repository";
import type { StorageService } from "fusion/storage/management/StorageService";
import { action } from "fusion/registries/Action";

let log = getLogger('OptimisticProjectSyncService');

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
 * Does NOT own the store. Does NOT touch the view model.
 * The store's onChange callback is the view model's concern.
 */
export class OptimisticProjectSyncService {
    private _store: Store;
    private _storageService: StorageService;
    private _projectId: string;

    private _localCommitGraph: CommitGraph;
    private _currentBranch: string;
    private _uncommittedDelta: Delta = new Delta({});
    private _expectedDelta: Delta = new Delta({});

    constructor(store: Store, storageService: StorageService, projectId: string, currentBranch: string) {
        this._store = store;
        this._storageService = storageService;
        this._projectId = projectId;
        this._currentBranch = currentBranch;
        this._localCommitGraph = new CommitGraph();
    }

    get uncommittedDelta(): Delta {
        return this._uncommittedDelta;
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
            this._uncommittedDelta.mergeWithPriority(delta);
        }
    }

    /**
     * Send accumulated uncommitted changes as a commit to the authority.
     * To be called from the root-action-completed hook.
     */
    saveUncommittedChanges() {
        if (this._uncommittedDelta.isEmpty()) {
            return;
        }

        log.info('Flushing uncommitted delta');

        let delta = this._uncommittedDelta;
        this._uncommittedDelta = new Delta({});
        this._expectedDelta.mergeWithPriority(delta);

        this._storageService.commit(this._projectId, delta.data, 'Auto-commit')
            .then((result) => {
                const appliedDeltaData = result.commit.deltaData;
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
                log.error('Auto-commit failed. Discarded uncommitted delta.', {
                    error,
                    projectId: this._projectId,
                    delta: delta.data,
                });
            });
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
