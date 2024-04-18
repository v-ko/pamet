import { WebAppState } from "./containers/app/App";
import { Channel, addChannel } from 'pyfusion/libs/Channel';
import { getLogger } from 'pyfusion/logging';
import { Repository, SearchFilter } from 'pyfusion/storage/BaseRepository';
import { InMemoryRepository } from 'pyfusion/storage/InMemoryRepository';
import { ActionState } from 'pyfusion/libs/Action';
import { Change } from "pyfusion/Change";
import { PametRepository } from "./storage/base";
import { fusion } from "pyfusion/index"
import { Entity, EntityData } from "pyfusion/libs/Entity";
import { ApiClient } from "./storage/ApiClient";
import { Page } from "./model/Page";
import { appActions } from "./actions/app";
import { Note } from "./model/Note";
import { Arrow } from "./model/Arrow";

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

        this._apiClient = new ApiClient('http://localhost', 3333, '', true);

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
                else if (changeOrActionState.completed && this._changeBufferForRootAction.length > 0) {
                    this.entityChangeListPerRootActionChannel.push(this._changeBufferForRootAction);
                }
            }
            else {
                this._changeBufferForRootAction.push(changeOrActionState);
            }
        });

        // Test the entityChangeListPerRootActionChannel by logging
        this.entityChangeListPerRootActionChannel.subscribe((changeList: Array<Change>) => {
            // List all changes
            log.info('entityChangeListPerRootActionChannel channel changes:');
            changeList.forEach((change) => {
                log.info(change);
            });
        });
    }

    pametSchemaToHttpUrl(url: string): string {
        if (!url.startsWith('pamet:')) {
            throw Error('Invalid media url: ' + url)
        }
        url = url.slice('pamet:'.length);
        return this._apiClient.endpointUrl(url);
    }

    _pushChangeToRawChannels(change: Change) {
        this.rawChagesChannel.push(change);
        this.rawChagesByIdChannel.push(change);
        this.rawChagesByParentIdChannel.push(change);
    }

    setWebAppState(state: WebAppState) {
        this._appState = state;
    }

    get appState(): WebAppState {
        if (!this._appState) {
            throw new Error('WebAppState not set');
        }
        return this._appState;
    }

    loadAllEntitiesTMP(callback_done: () => void) {
        console.log('Loading all entities')
        // Load page metadata, then load the children for all pages
        this._apiClient.pages().then((pages) => {

            // Map over the pages and return an array of promises
            const promises = pages.map((page) => {
                // this._loadPage(page);
                this._loadOne(page);

                // Return a promise that resolves when the children are loaded
                return this._apiClient.children(page.id).then((children) => {
                    let notes = children.notes;
                    let arrows = children.arrows;

                    // console.log('Loading children for page', page.id, 'notes', notes, 'arrows', arrows)

                    notes.forEach((note) => {
                        // this._loadOneNote(note);
                        this._loadOne(note);
                    });

                    arrows.forEach((arrow) => {
                        // this._loadOneArrow(arrow);
                        this._loadOne(arrow);
                    });
                });
            });

            // Wait for all the promises to resolve, then call callback_done
            Promise.all(promises).then(callback_done);
        });


    }

    apiClient() {
        return this._apiClient;
    }

    _loadOne(entity: Entity<EntityData>) {
        // Will be removed when the load/sync service is implemented
        try{
        this._syncRepo.insertOne(entity);
        } catch (e) {
            console.log('Error loading entity', entity, e)
        }
    }

    // Implement the Repository interface to use the InMemoryRepository
    insertOne(entity: Entity<EntityData>): Change {
        let change = this._syncRepo.insertOne(entity);
        this.applyChangesToViewStates([change]);
        this.rawChagesChannel.push(change);
        return change;
    }

    updateOne(entity: Entity<EntityData>): Change {
        let change = this._syncRepo.updateOne(entity);
        this.applyChangesToViewStates([change]);
        this.rawChagesChannel.push(change);
        return change;
    }
    removeOne(entity: Entity<EntityData>): Change {
        let change = this._syncRepo.removeOne(entity);
        this.applyChangesToViewStates([change]);
        this.rawChagesChannel.push(change);
        return change;
    }

    find(filter: SearchFilter = {}): Generator<Entity<EntityData>> {
        return this._syncRepo.find(filter);
    }

    findOne(filter: SearchFilter): Entity<EntityData> | undefined {
        return this._syncRepo.findOne(filter);
    }

    applyChangesToViewStates(changes: Array<Change>) {
        /** A reducer-like function to map entity changes to ViewStates
         * Will be used synchrously from the facade entity CRUD methods (inside actions)
         * And will be used by the domain store watcher service (responcible for
         * updating the view states after external domain store changes)
         */
        console.log('Applying changes to view states', changes)
        for (let change of changes) {
            // if page
            let entity = change.lastState;
            if (entity instanceof Page) {
                // get current page vs
                let pageVS = this.appState.currentPageViewState;
                if (!pageVS || pageVS.page.id !== entity.id) {
                    continue;
                }

                // if (change.isCreate()) // pass
                if (change.isDelete()) {
                    // remove
                    if (pageVS.page.id === entity.id) { // If current is removed
                        appActions.setPageToHomeOrFirst(this.appState);
                    }
                }
                else if (change.isUpdate()) {
                    // update data
                    pageVS.updateFromPage(entity);
                }
            }
            else if (entity instanceof Note || entity instanceof Arrow) {
                // get current page vs
                let pageVS = this.appState.currentPageViewState;
                if (!pageVS || pageVS.page.id !== entity.parentId) {
                    continue;
                }

                if (change.isCreate()) {
                    pageVS.addViewStateForElement(entity);
                }else if (change.isDelete()) {
                    pageVS.removeViewStateForElement(entity);
                }
                else if (change.isUpdate()) {
                    pageVS.updateEVS_fromElement(entity);
                }
            }
        }
    }
}

export const pamet = new PametFacade();
