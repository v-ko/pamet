import { WebAppState } from "./containers/app/App";
import { Channel, addChannel } from './fusion/libs/Channel';
import { getLogger } from './fusion/logging';
import { Repository, SearchFilter } from './fusion/storage/BaseRepository';
// import { InMemoryRepository } from './fusion/storage/InMemoryRepository';
import { ActionState } from './fusion/libs/Action';
import { Change } from "./fusion/Change";
import { PametRepository } from "./storage/base";
import { fusion } from "./fusion"
import { Entity, EntityData } from "./fusion/libs/Entity";
import { ApiClient } from "./storage/ApiClient";
import { ObservableMap } from "mobx";
import { Page } from "./model/Page";
import { Note } from "./model/Note";
import { Arrow } from "./model/Arrow";

const log = getLogger('facade');

// Make that more specific as the API clears up
export interface PageQueryFilter { [key: string]: any }


export class PametFacade extends PametRepository {
    // private _syncRepo: Repository;
    private _pagesStore: ObservableMap<string, Page> = new ObservableMap();
    private _notesStore: ObservableMap<string, Note> = new ObservableMap();
    private _arrowsStore: ObservableMap<string, Arrow> = new ObservableMap();
    private _notesByParentId: ObservableMap<string, Set<Note>> = new ObservableMap();
    private _arrowsByParentId: ObservableMap<string, Set<Arrow>> = new ObservableMap();

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
        // this._syncRepo = new InMemoryRepository();

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

    get pageStore() {
        return this._pagesStore;
    }
    get noteStore() {
        return this._notesStore;
    }
    get arrowStore() {
        return this._arrowsStore;
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
                // this._syncRepo.insertOne(page)
                this._pagesStore.set(page.id, page);

                this._apiClient.children(page.id).then((children) => {
                    let notes = children.notes
                    let arrows = children.arrows

                    notes.forEach((note) => {
                        if (note.own_id === 'e0bc336c') {
                            console.log('note', note)
                        }
                        // this._syncRepo.insertOne(note)
                        this._notesStore.set(note.id, note);
                    })
                    arrows.forEach((arrow) => {
                        // this._syncRepo.insertOne(arrow)
                        this._arrowsStore.set(arrow.id, arrow);
                    })

                    // log.info('Pages', Array.from(this.pages()))

                    // Signal loading done
                    callback_done()
                })
            });
        });
    }

    // repo() {
    //     return this._syncRepo;
    // }

    // setRepo(repo: Repository) {
    //     this._syncRepo = repo;
    // }



    apiClient() {
        return this._apiClient;
    }

    // Implement the Repository interface to use the InMemoryRepository
    insertOne(entity: Entity<EntityData>): Change {
        // let change = this._syncRepo.insertOne(entity);
        let change = Change.create(entity);
        if(entity instanceof Page){
            if (this._pagesStore.has(entity.id)) {
                throw new Error('Page with id ' + entity.id + ' already exists');
            }
            this._pagesStore.set(entity.id, entity);
        }
        else if(entity instanceof Note){
            if (this._notesStore.has(entity.id)) {
                throw new Error('Note with id ' + entity.id + ' already exists');
            }
            this._notesStore.set(entity.id, entity);
            // this._perParentIndex.set(entity.parentId, entity);
        }
        else if(entity instanceof Arrow){
            if (this._arrowsStore.has(entity.id)) {
                throw new Error('Arrow with id ' + entity.id + ' already exists');
            }
            this._arrowsStore.set(entity.id, entity);
            // this._arrowsByParentId.set(entity.parentId, entity);
        }
        this.rawChagesChannel.push(change);
        return change;
    }
   
    *find(filter: SearchFilter = {}): Generator<Entity<EntityData>, void, unknown> {
        let { id, type, parentId, ...otherFilters } = filter;

        let matches: Entity<EntityData>[] = []; // Initialize matches as an empty array

        // If id is defined
        if (id !== undefined) {
            if(type === Page){
                let match = this._pagesStore.get(id);
                if(match){
                    matches.push(match); // Directly add the single match
                }
            }
            else if(type === Note){
                let match = this._notesStore.get(id);
                if(match){
                    matches.push(match); // Directly add the single match
                }
            }
            else if(type === Arrow){
                let match = this._arrowsStore.get(id);
                if(match){
                    matches.push(match); // Directly add the single match
                }
            }
            else{
                // For each type, attempt to add the match directly if it exists
                let pageMatch = this._pagesStore.get(id);
                if(pageMatch){
                    matches.push(pageMatch);
                }
                let noteMatch = this._notesStore.get(id);
                if(noteMatch){
                    matches.push(noteMatch);
                }
                let arrowMatch = this._arrowsStore.get(id);
                if(arrowMatch){
                    matches.push(arrowMatch);
                }
            }
        }
        // If parentId is defined
        else if (parentId !== undefined) {
            if(type === Note){
                let notes = this._notesByParentId.get(parentId);
                if(notes){
                    matches.push(...notes); // Extend the matches array with notes
                }
            }
            else if(type === Arrow){
                let arrows = this._arrowsByParentId.get(parentId);
                if(arrows){
                    matches.push(...arrows); // Extend the matches array with arrows
                }
            }
            else{
                // Add notes and arrows associated with the parentId
                let notes = this._notesByParentId.get(parentId);
                if(notes){
                    matches.push(...notes);
                }
                let arrows = this._arrowsByParentId.get(parentId);
                if(arrows){
                    matches.push(...arrows);
                }
            }
        }
        else if(type){
            // If a specific type is provided, add all entities of that type
            if(type === Page){
                matches.push(...Array.from(this._pagesStore.values()));
            }
            else if(type === Note){
                matches.push(...Array.from(this._notesStore.values()));
            }
            else if(type === Arrow){
                matches.push(...Array.from(this._arrowsStore.values()));
            }
        }
        else{
            // If no specific type or parentId is provided, add all entities
            matches.push(...Array.from(this._pagesStore.values()));
            matches.push(...Array.from(this._notesStore.values()));
            matches.push(...Array.from(this._arrowsStore.values()));
        }

        // Filter the collected matches based on otherFilters and yield the valid ones
        for (let match of matches) {
            let matchIsValid = true;
            for (let key in otherFilters) {
                if (match[key] !== otherFilters[key]) {
                    matchIsValid = false;
                    break;
                }
            }
            if (matchIsValid) {
                yield match;
            }
        }
    }

    findOne(filter: SearchFilter): Entity<EntityData> | undefined {
        let result = this.find(filter).next();
        if (result.done) {
            return undefined;
        }
        return result.value;
        // return this.find(filter).next().value;
    }
    updateOne(entity: Entity<EntityData>): Change {
        // let change = this._syncRepo.updateOne(entity);
        let oldState = this.findOne({ id: entity.id });
        if (!oldState) {
            throw new Error('Entity with id ' + entity.id + ' does not exist');
        }
        let change = Change.update(oldState, entity);
        if(entity instanceof Page){
            this._pagesStore.set(entity.id, entity);
        }
        else if(entity instanceof Note){
            this._notesStore.set(entity.id, entity);
        }
        else if(entity instanceof Arrow){
            this._arrowsStore.set(entity.id, entity);
        }

        this.rawChagesChannel.push(change);
        return change;
    }
    removeOne(entity: Entity<EntityData>): Change {
        // let change = this._syncRepo.removeOne(entity);
        let oldState = this.findOne({ id: entity.id });
        if (!oldState) {
            throw new Error('Entity with id ' + entity.id + ' does not exist');
        }
        let change = Change.delete(oldState);
        if(entity instanceof Page){
            this._pagesStore.delete(entity.id);
        }
        else if(entity instanceof Note){
            this._notesStore.delete(entity.id);
        }
        else if(entity instanceof Arrow){
            this._arrowsStore.delete(entity.id);
        }
        this.rawChagesChannel.push(change);
        return change;
    }

    // Entity CRUD


    // Pages CRUD
    // pages(filter){

    // }
}

export const pamet = new PametFacade();
