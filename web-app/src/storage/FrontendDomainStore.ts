import { InMemoryStore } from "fusion/storage/domain-store/InMemoryStore"
import { PametStore as PametStore, PAMET_INMEMORY_STORE_CONFIG } from "@/storage/PametStore";
import { SearchFilter, SerializedStoreData, Store } from "fusion/storage/domain-store/BaseStore"
import { Entity, EntityData } from "fusion/model/Entity";
import { Change } from "fusion/model/Change";
import { entityDeltaToViewModelReducer, pamet } from "@/core/facade";
import { action } from "fusion/registries/Action";
import { getLogger } from "fusion/logging";
import { Delta } from "fusion/model/Delta";
import type { RepoUpdateData } from "fusion/storage/repository/Repository";
import { CommitGraph } from "fusion/storage/version-control/CommitGraph";
import { Commit } from "fusion/storage/version-control/Commit";
import { computeRepoSyncDelta } from "fusion/storage/management/sync-utils";

let log = getLogger('FrontendDomainStore');

export class FrontendDomainStore extends PametStore {
    /**
     * This is a wrapper for the in-memory domain store (used by the frontend)
     * where changes made in actions are appllied synchronously.
     *
     * This class can automatically produce commits for each store modification.
     * Due to the async nature of the repo service, and the possibility of
     * receiving commits auto-pulled from other sources (e.g. other devices, users)
     * we need to handle the case where a local change is applied, but the remote
     * commit is pushed before the local commit is produced. In this case, the local
     * changes should be reverted and the remote commit applied in order.
     * This class handles this synchronization without concerning the frontend.
     *
     */
    _store: Store;
    private _localCommitGraph: CommitGraph;
    private _currentBranch: string | null = null;

    private _uncommittedChanges: Change[] = [];
    // private _expectedDeltas: DeltaData[] = []; // Sent to the repo service to create commits with
    private _expectedChanges: Change[] = [];
    private _expectedDelta: Delta = new Delta({})

    constructor() {
        super()
        // Use Pamet-specific index configuration with entity type support
        this._store = new InMemoryStore(PAMET_INMEMORY_STORE_CONFIG);
        this._localCommitGraph = new CommitGraph();
    }
    data(): SerializedStoreData {
        return this._store.data();
    }
    loadData(data: SerializedStoreData): void {
        this._store.loadData(data);
    }

    /**
     * Initialize the FDS by hydrating from the storage service.
     * This mimics the Repository.pull logic.
     */
    async initialize(projectId: string, currentBranch: string): Promise<void> {
        try {
            // Get the remote commit graph and any commits we need
            const remoteGraphData = await pamet.storageService.getCommitGraph(projectId);
            const remoteGraph = CommitGraph.fromData(remoteGraphData);

            // For initial load, we assume local graph is empty but create the default branch
            const emptyLocalGraph = new CommitGraph();
            emptyLocalGraph.createBranch(currentBranch);

            // Get all commits from the remote (for initial hydration)
            const allCommits = remoteGraph.commits();
            const allCommitIds = allCommits.map(c => c.id);
            let upsertedCommits: Commit[] = [];

            if (allCommitIds.length > 0) {
                const commitDataArray = await pamet.storageService.getCommits(projectId, allCommitIds);
                upsertedCommits = commitDataArray.map(data => new Commit(data));
            }

            // Use the pure function to compute what delta to apply
            const syncDelta = computeRepoSyncDelta(emptyLocalGraph, remoteGraph, upsertedCommits, currentBranch);            if (syncDelta) {
                // Apply the delta to get the store in sync
                this._store.applyDelta(syncDelta);
                // Apply to view model
                entityDeltaToViewModelReducer(pamet.appViewState, syncDelta);
            }

            // Update our local commit graph to match remote and store current branch
            this._localCommitGraph = remoteGraph;
            this._currentBranch = currentBranch;

            log.info('FDS initialized successfully');
        } catch (error) {
            log.error('Failed to initialize FDS:', error);
            throw error;
        }
    }

    get uncommittedChanges(): Change[] {
        return this._uncommittedChanges;
    }

    _loadOne(entity: Entity<EntityData>) {
        // Will be removed when the load/sync service is implemented
        try {
            this._store.insertOne(entity);
        } catch (e) {
            console.log('Error loading entity', entity, e)
        }
    }

    // Implement the Repository interface to use the InMemoryRepository
    insertOne(entity: Entity<EntityData>): Change {
        // log.info('Inserting entity', entity);
        let change = this._store.insertOne(entity);
        entityDeltaToViewModelReducer(pamet.appViewState, Delta.fromChanges([change]));
        this._uncommittedChanges.push(change);
        return change;
    }

    updateOne(entity: Entity<EntityData>): Change {
        log.info('Updating entity', entity);
        let change = this._store.updateOne(entity);
        entityDeltaToViewModelReducer(pamet.appViewState, Delta.fromChanges([change]));
        if (!change.isEmpty()) {
            this._uncommittedChanges.push(change);
        } else if (pamet.debug) {
            log.warning('Update change is empty, not pushing to uncommitted changes', change);
        }
        return change;
    }
    removeOne(entity: Entity<EntityData>): Change {
        log.info('Removing entity', entity);
        let change = this._store.removeOne(entity);
        entityDeltaToViewModelReducer(pamet.appViewState, Delta.fromChanges([change]));
        this._uncommittedChanges.push(change);
        return change;
    }

    find(filter: SearchFilter = {}): Generator<Entity<EntityData>> {
        return this._store.find(filter);
    }

    findOne(filter: SearchFilter): Entity<EntityData> | undefined {
        let result = this._store.findOne(filter);
        return result
    }

    // Logic for committing, confirming commit creation and acceptiong new commits
    saveUncommitedChanges() {
        // To be called at the end of actions. Register as middleware in the facade

        // Produce delta from uncommitted changes
        if (this._uncommittedChanges.length === 0) {
            return;
        }

        log.info('Saving uncommited changes. Count:', this._uncommittedChanges.length)

        let delta = Delta.fromChanges(this._uncommittedChanges);
        this._uncommittedChanges = []
        this._expectedDelta.mergeWithPriority(delta);

        // Send the delta to the storage service
        let currentProject = pamet.appViewState.getCurrentProject();
        pamet.storageService.commit(currentProject.id, delta.data, 'Auto-commit')
    }

    @action({ issuer: 'service' })
    receiveRepoUpdate(repoUpdate: RepoUpdateData) {
        log.info('Received repo update', repoUpdate);

        try {
            // Convert the repo update data to objects
            const remoteGraph = CommitGraph.fromData(repoUpdate.commitGraph);
            const upsertedCommits = repoUpdate.upsertedCommits.map(data => new Commit(data));

            // Use the stored current branch or default to the first branch
            if (!this._currentBranch) {
                log.error('Current branch not set, FDS may not be initialized properly');
                return;
            }

            // Use the pure function to compute the delta needed for sync
            const repoSyncDelta = computeRepoSyncDelta(this._localCommitGraph, remoteGraph, upsertedCommits, this._currentBranch);

            if (!repoSyncDelta) {
                log.info('No repo sync changes needed');
                return;
            }

            // Reverse the expected delta and merge it with the repo sync delta
            // This handles the case where local changes were made but remote changes also occurred
            // What happens in detail:
            // 1. User makes change in action and the change is applied synchronously
            // in the FDS._store (lets call it S1), and the change/delta - C.
            // So S2 = S1 + C
            // 2. We save the change and request a commit with it. It's created in
            // the storage service. It has the same state S, but also may receive
            // changes from elsewhere, so we assume that the commit hash is
            // f(S2'), where C' are the expected changes +- other stuff, and S2'=S1+C'
            // 3. We receive the new commit and accept it as ground truth. But we
            // need to sync the FDS._store to the StorageService state.
            // So we do:
            // S2 - C = S1
            // S1 + C' = S2'
            // Or for efficiency sake we combine the deltas before applying them
            // (order matters)
            // S2 + (reversed(C) + C') = S2'
            let reversedExpectedDelta = this._expectedDelta.reversed();
            this._expectedDelta = new Delta({});

            // Combine the deltas: first reverse local changes, then apply remote changes
            reversedExpectedDelta.mergeWithPriority(repoSyncDelta);
            let finalDelta = reversedExpectedDelta;

            // Apply the combined delta to the store
            this._store.applyDelta(finalDelta);

            // Apply to view model
            entityDeltaToViewModelReducer(pamet.appViewState, finalDelta);

            // Update our local commit graph to match remote
            this._localCommitGraph = remoteGraph;

            log.info('Successfully applied repo update');
        } catch (e) {
            log.error('Error applying repo update:', e);
            alert('Critical error (check the console). Please reload the page');
        }
    }
}
