import { InMemoryStore } from "pyfusion/storage/InMemoryStore"
import { PametStore as PametStore } from "./PametStore";
import { SearchFilter, Store as Store } from "pyfusion/storage/BaseStore"
import { Entity, EntityData } from "pyfusion/libs/Entity";
import { Change, Delta } from "pyfusion/Change";
import { WebAppState } from "../containers/app/App";
import { applyChangesToViewModel } from "../core/facade";
import { registerRootActionCompletedHook } from "pyfusion/libs/Action";
import { getLogger } from "pyfusion/logging";

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
    private _appState: WebAppState;
    // private _repoService: RepositoryServiceWrapper;

    private _uncommittedChanges: Change[] = [];
    private _expectedDeltas: Delta[] = []; // Sent to the repo service to create commits with

    constructor(appState: WebAppState) {
        super()
        this._store = new InMemoryStore();
        this._appState = appState;
        // this._repoService = repositoryService

        // Register rootAction hook to auto-commit - THIS SHOULD GO IN THE FACADE
        let autoCommit = true;
        if (autoCommit) {
            registerRootActionCompletedHook(() => {
                if (this._uncommittedChanges.length === 0) {
                    return;
                }
                log.info('registerRootActionCompletedHook triggered. Committing changes:');
                this._uncommittedChanges.forEach((change) => {
                    log.info(change);
                });
                this.clearUncommittedChanges();
            });
        }
    }

    get uncommittedChanges(): Change[] {
        return this._uncommittedChanges;
    }
    clearUncommittedChanges() {
        this._uncommittedChanges = [];
    }

    _loadOne(entity: Entity<EntityData>) {
        // Will be removed when the load/sync service is implemented
        try{
        this._store.insertOne(entity);
        } catch (e) {
            console.log('Error loading entity', entity, e)
        }
    }

    // Implement the Repository interface to use the InMemoryRepository
    insertOne(entity: Entity<EntityData>): Change {
        let change = this._store.insertOne(entity);
        applyChangesToViewModel(this._appState, [change]);
        this._uncommittedChanges.push(change);
        return change;
    }

    updateOne(entity: Entity<EntityData>): Change {
        let change = this._store.updateOne(entity);
        applyChangesToViewModel(this._appState, [change]);
        this._uncommittedChanges.push(change);
        return change;
    }
    removeOne(entity: Entity<EntityData>): Change {
        let change = this._store.removeOne(entity);
        applyChangesToViewModel(this._appState, [change]);
        this._uncommittedChanges.push(change);
        return change;
    }

    find(filter: SearchFilter = {}): Generator<Entity<EntityData>> {
        return this._store.find(filter);
    }

    findOne(filter: SearchFilter): Entity<EntityData> | undefined {
        return this._store.findOne(filter);
    }

    _requestCommitCreation(delta: Delta) {
        log.info('Requesting commit creation for delta:', delta);
        this._expectedDeltas.push(delta);

    }

}
