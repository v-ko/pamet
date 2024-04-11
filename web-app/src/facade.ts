import { WebAppState } from "./containers/app/App";
import { Channel, addChannel } from 'pyfusion/libs/Channel';
import { getLogger } from 'pyfusion/logging';
import { SearchFilter } from 'pyfusion/storage/BaseRepository';
// import { InMemoryRepository } from 'pyfusion/storage/InMemoryRepository';
import { ActionState } from 'pyfusion/libs/Action';
import { Change } from "pyfusion/Change";
import { PametRepository } from "./storage/base";
import { fusion } from "pyfusion/index"
import { Entity, EntityData } from "pyfusion/libs/Entity";
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
    pageStore: ObservableMap<string, Page> = new ObservableMap();
    noteStore: ObservableMap<string, Note> = new ObservableMap();
    arrowStore: ObservableMap<string, Arrow> = new ObservableMap();
    noteStoresByParentId: ObservableMap<string, ObservableMap<string, Note>> = new ObservableMap();
    arrowStoresByParentId: ObservableMap<string, ObservableMap<string, Arrow>> = new ObservableMap();

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
            // if (!changeList.length) {
            //     return;
            // }
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
        // Load page metadata, then load the children for all pages
        this._apiClient.pages().then((pages) => {

            // Map over the pages and return an array of promises
            const promises = pages.map((page) => {
                this._loadPage(page);

                // Return a promise that resolves when the children are loaded
                return this._apiClient.children(page.id).then((children) => {
                    let notes = children.notes;
                    let arrows = children.arrows;

                    // console.log('Loading children for page', page.id, 'notes', notes, 'arrows', arrows)

                    notes.forEach((note) => {
                        this._loadOneNote(note);
                    });

                    arrows.forEach((arrow) => {
                        this._loadOneArrow(arrow);
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

    _loadPage(page: Page) {
        if (this.pageStore.has(page.id)) {
            throw new Error('Page with id ' + page.id + ' already exists');
        }
        this.pageStore.set(page.id, page);

        // Create a note store for the page
        if (this.noteStoresByParentId.get(page.id) !== undefined) {
            throw new Error('Note store for page with id ' + page.id + ' already exists');
        }
        this.noteStoresByParentId.set(page.id, new ObservableMap());
    }

    _loadOneNote(note: Note) {
        console.log('loading note', note)
        if (this.noteStore.has(note.id)) {
            throw new Error('Note with id ' + note.id + ' already exists');
        }
        this.noteStore.set(note.id, note);

        // Update the per parent index
        let perParentStore = this.noteStoresByParentId.get(note.parentId);
        if (perParentStore === undefined) {
            throw new Error('Notes by parent id ' + note.parentId + ' does not exist');
        }
        perParentStore.set(note.id, note);
    }

    _loadOneArrow(arrow: Arrow) {
        if (this.arrowStore.has(arrow.id)) {
            throw new Error('Arrow with id ' + arrow.id + ' already exists');
        }
        this.arrowStore.set(arrow.id, arrow);

        // Update the per parent index
        let perParentStore = this.arrowStoresByParentId.get(arrow.parentId);
        if (perParentStore === undefined) {
            this.arrowStoresByParentId.set(arrow.parentId, new ObservableMap());
        }
        else {
            perParentStore.set(arrow.id, arrow);
        }
    }

    // Implement the Repository interface to use the InMemoryRepository
    insertOne(entity: Entity<EntityData>): Change {
        // let change = this._syncRepo.insertOne(entity);
        let change = Change.create(entity);
        if (entity instanceof Page) {
            if (this.pageStore.has(entity.id)) {
                throw new Error('Page with id ' + entity.id + ' already exists');
            }
            this._loadPage(entity);
        }
        else if (entity instanceof Note) {
            this._loadOneNote(entity);
        }
        else if (entity instanceof Arrow) {
            this._loadOneArrow(entity);
        }
        this.rawChagesChannel.push(change);
        return change;
    }

    *find(filter: SearchFilter = {}): Generator<Entity<EntityData>, void, unknown> {
        let { id, type, parentId, ...otherFilters } = filter;

        let matches: Entity<EntityData>[] = []; // Initialize matches as an empty array

        // If id is defined
        if (id !== undefined) {
            if (type === Page) {
                let match = this.pageStore.get(id);
                if (match) {
                    matches.push(match); // Directly add the single match
                }
            }
            else if (type === Note) {
                let match = this.noteStore.get(id);
                if (match) {
                    matches.push(match); // Directly add the single match
                }
            }
            else if (type === Arrow) {
                let match = this.arrowStore.get(id);
                if (match) {
                    matches.push(match); // Directly add the single match
                }
            }
            else {
                // For each type, attempt to add the match directly if it exists
                let pageMatch = this.pageStore.get(id);
                if (pageMatch) {
                    matches.push(pageMatch);
                }
                let noteMatch = this.noteStore.get(id);
                if (noteMatch) {
                    matches.push(noteMatch);
                }
                let arrowMatch = this.arrowStore.get(id);
                if (arrowMatch) {
                    matches.push(arrowMatch);
                }
            }
        }
        // If parentId is defined
        else if (parentId !== undefined) {
            if (type === Note) {
                let noteStoreForPageId = this.noteStoresByParentId.get(parentId);
                if (noteStoreForPageId) {
                    matches.push(...noteStoreForPageId.values()); // Extend the matches array with notes
                }
            }
            else if (type === Arrow) {
                let arrowStoreForPageId = this.arrowStoresByParentId.get(parentId);
                if (arrowStoreForPageId) {
                    matches.push(...arrowStoreForPageId.values()); // Extend the matches array with arrows
                }
            }
            else {
                // Add notes and arrows associated with the parentId
                let noteStoreForPageId = this.noteStoresByParentId.get(parentId);
                if (noteStoreForPageId) {
                    matches.push(...noteStoreForPageId.values());
                }
                let arrowStoreForPageId = this.arrowStoresByParentId.get(parentId);
                if (arrowStoreForPageId) {
                    matches.push(...arrowStoreForPageId.values());
                }
            }
        }
        else if (type) {
            // If a specific type is provided, add all entities of that type
            if (type === Page) {
                matches.push(...Array.from(this.pageStore.values()));
            }
            else if (type === Note) {
                matches.push(...Array.from(this.noteStore.values()));
            }
            else if (type === Arrow) {
                matches.push(...Array.from(this.arrowStore.values()));
            }
        }
        else {
            // If no specific type or parentId is provided, add all entities
            matches.push(...Array.from(this.pageStore.values()));
            matches.push(...Array.from(this.noteStore.values()));
            matches.push(...Array.from(this.arrowStore.values()));
        }

        // Filter the collected matches based on otherFilters and yield the valid ones
        for (let match of matches as Record<string, any>[]) {
            let matchIsValid = true;
            for (let key in otherFilters) {
                if (match[key] !== otherFilters[key]) {
                    matchIsValid = false;
                    break;
                }
            }
            if (matchIsValid) {
                yield match as Entity<EntityData>;
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
        if (entity instanceof Page) {
            this.pageStore.set(entity.id, entity);
        }
        else if (entity instanceof Note) {
            this.noteStore.set(entity.id, entity);
            // Update the per parent index
            let noteStoreForPageId = this.noteStoresByParentId.get(entity.parentId);
            if (!noteStoreForPageId) {
                throw new Error('Notes by parent id ' + entity.parentId + ' does not exist');
            }
            noteStoreForPageId.set(entity.id, entity);
        }
        else if (entity instanceof Arrow) {
            this.arrowStore.set(entity.id, entity);
            // Update the per parent index
            let arrowStoreForPageId = this.arrowStoresByParentId.get(entity.parentId);
            if (!arrowStoreForPageId) {
                throw new Error('Arrows by parent id ' + entity.parentId + ' does not exist');
            }
            arrowStoreForPageId.set(entity.id, entity)
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
        if (entity instanceof Page) {
            this.pageStore.delete(entity.id);
            // Remove notes store for the page?
        }
        else if (entity instanceof Note) {
            this.noteStore.delete(entity.id);
            // Update the per parent index
            let noteStoreForPageId = this.noteStoresByParentId.get(entity.parentId);
            if (!noteStoreForPageId) {
                throw new Error('Notes by parent id ' + entity.parentId + ' does not exist');
            }
            noteStoreForPageId.delete(entity.id);
        }
        else if (entity instanceof Arrow) {
            this.arrowStore.delete(entity.id);
            // Update the per parent index
            let arrowStoreForPageId = this.arrowStoresByParentId.get(entity.parentId);
            if (!arrowStoreForPageId) {
                throw new Error('Arrows by parent id ' + entity.parentId + ' does not exist');
            }
            arrowStoreForPageId.delete(entity.id);
        }
        this.rawChagesChannel.push(change);
        return change;
    }
}

export const pamet = new PametFacade();
