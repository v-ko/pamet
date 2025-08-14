import { InMemoryStore } from "fusion/storage/domain-store/InMemoryStore"
import { PametStore as PametStore, PAMET_INMEMORY_STORE_CONFIG } from "@/storage/PametStore";
import { SearchFilter, SerializedStoreData, Store } from "fusion/storage/domain-store/BaseStore"
import { Entity, EntityData } from "fusion/model/Entity";
import { Change } from "fusion/model/Change";
import { updateViewModelFromDelta, pamet } from "@/core/facade";
import { action } from "fusion/registries/Action";
import { getLogger } from "fusion/logging";
import { Delta, DeltaData, squishDeltas } from "fusion/model/Delta";
import type { RepoUpdateData } from "fusion/storage/repository/Repository";

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

    private _uncommittedChanges: Change[] = [];
    // private _expectedDeltas: DeltaData[] = []; // Sent to the repo service to create commits with
    private _expectedChanges: Change[] = [];
    private _expectedDelta: Delta = new Delta({})

    constructor() {
        super()
        // Use Pamet-specific index configuration with entity type support
        this._store = new InMemoryStore(PAMET_INMEMORY_STORE_CONFIG);
    }
    data(): SerializedStoreData {
        return this._store.data();
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
        // log.info('Inserting entity', entity);
        let change = this._store.insertOne(entity);
        updateViewModelFromDelta(pamet.appViewState, Delta.fromChanges([change]));
        this._uncommittedChanges.push(change);
        return change;
    }

    updateOne(entity: Entity<EntityData>): Change {
        log.info('Updating entity', entity);
        let change = this._store.updateOne(entity);
        updateViewModelFromDelta(pamet.appViewState, Delta.fromChanges([change]));
        this._uncommittedChanges.push(change);
        return change;
    }
    removeOne(entity: Entity<EntityData>): Change {
        log.info('Removing entity', entity);
        let change = this._store.removeOne(entity);
        updateViewModelFromDelta(pamet.appViewState, Delta.fromChanges([change]));
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
        let currentProject = pamet.appViewState.currentProject();
        if (!currentProject) {
            throw Error('No current project set');
        }
        pamet.storageService.commit(currentProject.id, delta.data, 'Auto-commit')
    }

    @action({ issuer: 'service' })
    receiveRepoUpdate(repoUpdate: RepoUpdateData) {
        log.info('Received repo update', repoUpdate);

        // Aggregate the deltas from the commits
        let deltasData: DeltaData[] = []
        for (let commitData of repoUpdate.newCommits) {
            let deltaData = commitData.deltaData;
            if (deltaData === undefined) {
                throw Error('Received undefined delta data')
            }
            deltasData.push(deltaData)
        }
        let aggregatedDeltas = squishDeltas(deltasData);

        // Reverse the expected delta and merge it with the received one
        // The remainder is what we need to apply to get the store in sync
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

        try {
            reversedExpectedDelta.mergeWithPriority(aggregatedDeltas);
            let unexpectedDelta = reversedExpectedDelta;
            this._store.applyDelta(unexpectedDelta);

            // Apply the result to the repo
            updateViewModelFromDelta(pamet.appViewState, unexpectedDelta);
        } catch (e) {
            log.error('Inconsistency between received commit deltas and expected changes. Exception:', e);
            alert('Critical error (check the console). Please reload the page');
            // window.location.reload();
        }

        // // Check that the last commit hash is the same as the one of the
        // // store state after the update... Cannot be done, hashing is async.
        // // Also this class should be lean

        // // Integrity check (TMP)
        // // Check that the store hash is the same as the commit
        // let hashTreePromise = buildHashTree(this._store);
        // hashTreePromise.then((hashTree) => {
        //     let storeHash = hashTree.rootHash();
        //     let commitHash = repoUpdate.newCommits[repoUpdate.newCommits.length - 1].snapshotHash;
        //     if (storeHash !== commitHash) {
        //         log.error('Hash tree integrity check failed',
        //             'Current hash:', storeHash,
        //             'Expected hash:', commitHash);
        //     } else {
        //         log.info('FDS store hash equals commit hash');
        //         log.info('Store hash:', storeHash);
        //     }
        // }).catch((e) => {
        //     log.error('Error in hash tree building', e);
        // })
        // // Get head state from the store and compare with the FDS.inMemoryRepo
        // let headStatePromise = pamet.storageService.headState(
        //     pamet.appViewState.currentProjectId!)

        // headStatePromise.then((headState) => {
        //     log.info('Head state', JSON.stringify(headState, null, 2));
        //     let store = new InMemoryStore();
        //     store.loadData(headState);
        //     let headHashTreePromise = buildHashTree(store);
        //     headHashTreePromise.then((headHashTree) => {
        //         let headHash = headHashTree.rootHash();
        //         log.info('Head state hash:', headHash);
        //         let commitHash = repoUpdate.newCommits[repoUpdate.newCommits.length - 1].snapshotHash;
        //         if (headHash !== commitHash) {
        //             log.error('Head state integrity check failed',
        //                 'FDS hash:', headHash,
        //                 'Commit hash:', headHash);
        //         } else{
        //             log.info('Head state hash equals commit hash');
        //             log.info('Head state hash:', headHash);
        //         }
        //     }).catch((e) => {
        //         log.error('Error in head hash tree', e);
        //     })
        // }).catch((e) => {
        //     log.error('Error in head state', e);
        // })
    }
}
