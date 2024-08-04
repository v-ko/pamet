import { InMemoryStore } from "fusion/storage/InMemoryStore"
import { PametStore as PametStore } from "./PametStore";
import { SearchFilter, SerializedStoreData, Store as Store, deltaFromChanges } from "fusion/storage/BaseStore"
import { Entity, EntityData } from "fusion/libs/Entity";
import { Change } from "fusion/Change";
import { updateViewModelFromChanges, pamet } from "../core/facade";
import { action } from "fusion/libs/Action";
import { getLogger } from "fusion/logging";
import { Delta, DeltaData } from "fusion/storage/Delta";
import type { RepoUpdate } from "../../../fusion/js-src/src/storage/BaseRepository";

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
    private _store: Store;

    private _uncommittedChanges: Change[] = [];
    private _expectedDeltas: DeltaData[] = []; // Sent to the repo service to create commits with

    constructor() {
        super()
        this._store = new InMemoryStore();
    }

    loadData(data: SerializedStoreData): void {
        this._store.loadData(data);
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
        log.info('Inserting entity', entity);
        console.trace()
        let change = this._store.insertOne(entity);
        updateViewModelFromChanges(pamet.appViewState, [change]);
        this._uncommittedChanges.push(change);
        return change;
    }

    updateOne(entity: Entity<EntityData>): Change {
        log.info('Updating entity', entity);
        let change = this._store.updateOne(entity);
        updateViewModelFromChanges(pamet.appViewState, [change]);
        this._uncommittedChanges.push(change);
        return change;
    }
    removeOne(entity: Entity<EntityData>): Change {
        log.info('Removing entity', entity);
        let change = this._store.removeOne(entity);
        updateViewModelFromChanges(pamet.appViewState, [change]);
        this._uncommittedChanges.push(change);
        return change;
    }

    find(filter: SearchFilter = {}): Generator<Entity<EntityData>> {
        return this._store.find(filter);
    }

    findOne(filter: SearchFilter): Entity<EntityData> | undefined {
        return this._store.findOne(filter);
    }

    // Logic for committing, confirming commit creation and acceptiong new commits
    saveUncommitedChanges() {
        // To be called at the end of actions. Register as middleware in the facade

        // Produce delta from uncommitted changes
        if (this._uncommittedChanges.length === 0) {
            return;
        }

        log.info('Saving uncommited changes. Count:', this._uncommittedChanges.length)

        let delta = deltaFromChanges(this._uncommittedChanges);
        this._uncommittedChanges = []
        this._expectedDeltas.push(delta.data);

        // Send the delta to the storage service
        let currentProject = pamet.currentProject();
        if (!currentProject) {
            throw Error('No current project set');
        }
        pamet.storageService.commit(currentProject.id, delta.data, 'Auto-commit')
    }

    @action({issuer: 'service'})
    receiveRepoUpdate(repoUpdate: RepoUpdate) {
        log.info('Received repo update', repoUpdate);
        //     // Check if the update is expected
        //     // If expected - skip the commits that match the expected deltas
        //     // Else - revert the local changes and apply the received commits
        //     // (which will include the local changes with conclicting changes
        //     // overriden)
        //     let deltas: Delta[] = []
        //     let externalDeltas: Delta[] = []
        //     for (let commitData of repoUpdate.commits) {
        //         let deltaData = commitData.deltaData;
        //         if (deltaData === undefined) {
        //             throw Error('Received undefined delta data')
        //         }
        //         let delta = new Delta(deltaData);

        //         // If no expected deltas: add to external
        //         if (this._expectedDeltas.length === 0) {
        //             externalDeltas.push(delta)
        //         } else {  // Else if expecting
        //             let expectedDelta = this._expectedDeltas.shift();
        //             // - If match - continue (don't apply commit, and delta removed from expected)

        //             // - If mismatch - clear expected deltas

        //         }

        // Simpler: always revert and reapply. mobx will reduce changes already
        // sent to the views

        // Revert local changes by applying them in reversed order
        for (let change of this._uncommittedChanges) {
            this._store.applyChange(change.reversed())
        }

        // Apply external delta (which will include the local changes)
        let changes: Change[] = []
        for (let commitData of repoUpdate.newCommits) {
            let deltaData = commitData.deltaData;
            if (deltaData === undefined) {
                throw Error('Received undefined delta data')
            }
            let delta = new Delta(deltaData);
            let changes_ = this._store.applyDelta(delta)
            changes.push(...changes_)
        }
        updateViewModelFromChanges(pamet.appViewState, changes);
    }
}
