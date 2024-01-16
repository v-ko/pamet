import { WebAppState } from "./containers/app/App";
import { Channel, addChannel } from './fusion/libs/Channel';
import { getLogger } from './fusion/logging';
import { Repository, SearchFilter } from './fusion/storage/BaseRepository';
import { InMemoryRepository } from './fusion/storage/InMemoryRepository';
import { ActionState } from './fusion/libs/Action';
import { Change } from "./fusion/Change";
import { PametRepository } from "./storage/base";
import { fusion } from "./fusion"
import { Entity, EntityData } from "./fusion/libs/Entity";
import { ApiClient } from "./storage/ApiClient";

const log = getLogger('facade');

// Make that more specific as the API clears up
export interface PageQueryFilter { [key: string]: any }


export class PametFacade extends PametRepository {
    private _syncRepo: Repository;
    private _apiClient: ApiClient;
    private _appState?: WebAppState;
    private _changeBufferForRootAction: Array<Change> = [];

    rawChagesChannel: Channel;
    rawChagesByIdChannel: Channel;
    rawChagesByParentIdChannel: Channel;
    rawChangesPlusRootActionEventsChannel: Channel;
    entityChangeListPerRootActionChannel: Channel;

    constructor() {
        super()
        this._syncRepo = new InMemoryRepository();
        this._apiClient = new ApiClient('http://localhost', 3333);

        // Setup the change communication pipeline
        // The CRUD methods push changes to the rawChangesChannel
        this.rawChagesChannel = addChannel('rawChanges');
        this.rawChagesByIdChannel = addChannel('rawChangesById', (change) => change.entity.id);
        this.rawChagesByParentIdChannel = addChannel('rawChangesByParentId', (change) => change.entity.parentId);

        // Merge the rawChangesChannel and the rootActionEventsChannel
        this.rawChangesPlusRootActionEventsChannel = addChannel('rawChangesPlusRootActionEvents');
        this.rawChagesChannel.subscribe((change: Change) => {
            this.rawChangesPlusRootActionEventsChannel.push(change);
        });
        fusion.rootActionEventsChannel.subscribe((actionState: ActionState) => {
            this.rawChangesPlusRootActionEventsChannel.push(actionState);
        });

        // Group changes per root action
        this.entityChangeListPerRootActionChannel = addChannel('entityChangeListPerRootAction');
        this.rawChangesPlusRootActionEventsChannel.subscribe((changeOrActionState: Change | ActionState) => {
            if (changeOrActionState instanceof ActionState) {
                if (changeOrActionState.started) {
                    this._changeBufferForRootAction = [];
                }
                else if (changeOrActionState.completed) {
                    this.entityChangeListPerRootActionChannel.push(this._changeBufferForRootAction);
                }
            }
            else {
                this._changeBufferForRootAction.push(changeOrActionState);
            }
        });

        // Test the entityChangeListPerRootActionChannel by logging
        this.entityChangeListPerRootActionChannel.subscribe((changeList: Array<Change>) => {
            // if (!changeList.length) {
            //     return;
            // }
            // List all changes
            log.info('Changes:');
            changeList.forEach((change) => {
                log.info(change);
            });
        });
    }

    _pushChangeToRawChannels(change: Change) {
        this.rawChagesChannel.push(change);
        this.rawChagesByIdChannel.push(change);
        this.rawChagesByParentIdChannel.push(change);
    }

    // _actionParsingMiddleware = (call, next) => {
    //     let actionState = new ActionState(call.name);
    //     actionState.setStarted();

    //     this.rootActionEventsChannel.push(actionState);

    //     next(call);

    //     actionState = actionState.copy();
    //     actionState.setCompleted();
    //     this.rootActionEventsChannel.push(actionState);
    // }
    // Reimplement the above to use mobx spy


    setWebAppState(state: WebAppState) {
        this._appState = state;
    }

    loadAllEntitiesTMP(callback_done: () => void) {
        // Load page metadata, then load the children for all pages
        this._apiClient.pages().then((pages) => {

            pages.forEach((page) => {
                this._syncRepo.insertOne(page)
                this._apiClient.children(page.id).then((children) => {
                    let notes = children.notes
                    let arrows = children.arrows

                    notes.forEach((note) => {
                        if (note.own_id === 'e0bc336c') {
                            console.log('note', note)
                        }
                        this._syncRepo.insertOne(note)
                    })
                    arrows.forEach((arrow) => {
                        this._syncRepo.insertOne(arrow)
                    })

                    // log.info('Pages', Array.from(this.pages()))

                    // Signal loading done
                    callback_done()
                })
            });
        });
    }

    repo() {
        return this._syncRepo;
    }

    setRepo(repo: Repository) {
        this._syncRepo = repo;
    }

    apiClient() {
        return this._apiClient;
    }

    // Implement the Repository interface to use the InMemoryRepository
    insertOne(entity: Entity<EntityData>): Change {
        let change = this._syncRepo.insertOne(entity);
        this.rawChagesChannel.push(change);
        return change;
    }
    find<T extends Entity<EntityData>>(filter: SearchFilter = {}): Generator<T, any, unknown> {
        return this._syncRepo.find(filter);
    }

    findOne<T extends Entity<EntityData>>(filter: SearchFilter): T | undefined {
        return this._syncRepo.findOne(filter);
    }
    updateOne(entity: Entity<EntityData>): Change {
        let change = this._syncRepo.updateOne(entity);
        this.rawChagesChannel.push(change);
        return change;
    }
    removeOne(entity: Entity<EntityData>): Change {
        let change = this._syncRepo.removeOne(entity);
        this.rawChagesChannel.push(change);
        return change;
    }

    // Entity CRUD


    // Pages CRUD
    // pages(filter){

    // }
}

export const pamet = new PametFacade();
