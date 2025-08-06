import { WebAppState } from "../containers/app/WebAppState";
import { getLogger } from 'fusion/logging';
import { SearchFilter } from 'fusion/storage/BaseStore';
import { Change } from "fusion/Change";
import { PAMET_INMEMORY_STORE_CONFIG, PametStore } from "../storage/PametStore";
import { Entity, EntityData } from "fusion/libs/Entity";
import { ApiClient } from "../storage/ApiClient";
import { appActions } from "../actions/app";
import { Note } from "../model/Note";
import { Arrow } from "../model/Arrow";
import { MediaItem } from "fusion/libs/MediaItem";
import { FrontendDomainStore } from "../storage/FrontendDomainStore";
import { PametConfigService } from "../services/config/Config";
import { StorageService } from "fusion/storage/StorageService";
import { MediaStoreAdapterNames, ProjectStorageConfig, StorageAdapterNames } from "fusion/storage/ProjectStorageManager";
import { RepoUpdateData } from "fusion/storage/BaseRepository";
import { RoutingService } from "../services/routing/RoutingService";
import { PametRoute } from "../services/routing/route";
import { registerRootActionCompletedHook } from "fusion/libs/Action";
import { ProjectData } from "../model/config/Project";
import { KeybindingService } from "../services/KeybindingService";
import { commands } from "./commands";
import { FocusManager } from "../services/FocusManager";
import { Delta } from "fusion/storage/Delta";
import { updateAppStateFromConfig } from "../procedures/app";

const log = getLogger('facade');
const completedActionsLogger = getLogger('User action completed');

// Make that more specific as the API clears up
export interface PageQueryFilter { [key: string]: any }



// Service related
export function webStorageConfigFactory(projectId: string): ProjectStorageConfig {
    let device = pamet.config.deviceData;
    if (!device) {
        throw Error('Device not set');
    }
    return {
        currentBranchName: device.id,
        inMemoryRepoIndexConfigs: PAMET_INMEMORY_STORE_CONFIG,
        localRepo: {
            name: 'IndexedDB' as StorageAdapterNames,
            args: {
                projectId: projectId,
                localBranchName: device.id,
            }
        },
        localMediaStore: {
            name: 'CacheAPI' as MediaStoreAdapterNames,
            args: {
                projectId: projectId
            }
        }
    }
}


export class PametFacade extends PametStore {
    getEntityId() {
        throw new Error("Method not implemented.");
    }
    private _frontendDomainStore: FrontendDomainStore | null = null;
    private _apiClient: ApiClient;
    private _appViewState: WebAppState | null = null;
    private _config: PametConfigService | null = null;
    private _storageService: StorageService | null = null;
    router: RoutingService = new RoutingService();
    keybindingService: KeybindingService = new KeybindingService();
    focusService: FocusManager = new FocusManager();
    context: any = {};
    _projectStorageConfigFactory: ((projectId: string) => ProjectStorageConfig) | null = null
    // Focus handling (context related): Except when receiving focus/blur
    // events - the context change should be applied in the unmount hook
    // (callback returned by useEffect)

    constructor() {
        super()
        this._apiClient = new ApiClient('http://localhost', 3000, '', true);

        this.keybindingService.setKeybindings([
            // No modifier commands (assuming "when: noModifiers" is checked in contextConditionFulfilled):
            {
                key: 'n',
                command: commands.createNewNote.name,
                when: 'canvasFocus'
            },
            {
                key: 'e',
                command: commands.editSelectedNote.name,
                when: 'canvasFocus'
            },
            {
                key: 'l',
                command: commands.createArrow.name,
                when: 'canvasFocus'
            },
            {
                key: 'a',
                command: commands.autoSizeSelectedNotes.name,
                when: 'canvasFocus'
            },
            {
                key: 'escape',
                command: commands.cancelPageAction.name,
                when: 'canvasFocus'
            },
            {
                key: 'h',
                command: commands.showHelp.name,
                when: 'canvasFocus'
            },
            {
                key: 'delete',
                command: commands.deleteSelectedElements.name,
                when: 'canvasFocus'
            },
            {
                key: '1',
                command: commands.colorSelectedElementsPrimary.name,
                when: 'canvasFocus'
            },
            {
                key: '2',
                command: commands.colorSelectedElementsSuccess.name,
                when: 'canvasFocus'
            },
            {
                key: '3',
                command: commands.colorSelectedElementsError.name,
                when: 'canvasFocus'
            },
            {
                key: '4',
                command: commands.colorSelectedElementsSurfaceDim.name,
                when: 'canvasFocus'
            },
            {
                key: '5',
                command: commands.setNoteBackgroundToTransparent.name,
                when: 'canvasFocus'
            },
            {
                key: 'p',
                command: commands.createNewPage.name,
                when: 'canvasFocus'
            },

            {
                key: 'ctrl+=',
                command: commands.pageZoomIn.name,
                when: 'canvasFocus'
            },
            {
                key: 'ctrl+-',
                command: commands.pageZoomOut.name,
                when: 'canvasFocus'
            },
            {
                key: 'ctrl+0',
                command: commands.pageZoomReset.name,
                when: 'canvasFocus'
            },
            {
                key: 'ctrl+a',
                command: commands.selectAll.name,
                when: 'canvasFocus'
            },
            {
                key: 'ctrl+e',
                command: commands.openPageProperties.name,
                when: 'canvasFocus'
            },
            {
                key: 'ctrl+shift+y',  // tmp, could not find a sane shortcut
                command: commands.createNewPage.name,
                when: 'canvasFocus'
            },
            {
                key: 'ctrl+shift+u',  // tmp, could not find a sane shortcut
                command: commands.storeStateToClipboard.name,
                when: 'canvasFocus'
            },
            {
                key: 'ctrl+shift+v',
                command: commands.pasteSpecial.name,
                when: 'canvasFocus'
            },

        ]);

        // Register rootAction hook to auto-commit / save
        registerRootActionCompletedHook(() => {
            // Better do the registration here, so that we don't have to worry
            // about unregistering when swapping out the FDS
            if (!this._frontendDomainStore) {
                // log.warning('No frontend domain store set');
                return;
            }
            this.frontendDomainStore.saveUncommitedChanges()
        });

        // Register logger to root actions hooks
        registerRootActionCompletedHook((rootAction) => {
            if (rootAction.issuer !== 'user') {
                return;
            }
            completedActionsLogger.info(rootAction.name);
        });
    }

    get projectStorageConfigFactory(): (projectId: string) => ProjectStorageConfig {
        if (this._projectStorageConfigFactory === null) {
            throw Error('Project storage config factory not set');
        }
        return this._projectStorageConfigFactory;
    }

    setProjectStorageConfigFactory(factory: (projectId: string) => ProjectStorageConfig) {
        this._projectStorageConfigFactory = factory;
    }

    projectStorageConfig(projectId: string): ProjectStorageConfig {
        return this.projectStorageConfigFactory(projectId);
    }

    get frontendDomainStore(): FrontendDomainStore {
        if (!this._frontendDomainStore) {
            throw Error('Frontend domain store not set');
        }
        return this._frontendDomainStore;
    }

    removeFrontendDomainStore() {
        this._frontendDomainStore = null;
    }

    setFrontendDomainStore(store: FrontendDomainStore) {
        this._frontendDomainStore = store;
    }

    get apiClient() {
        return this._apiClient;
    }

    get storageService() {
        if (!this._storageService) {
            throw Error('Storage service not set');
        }
        return this._storageService;
    }
    setStorageService(storageService: StorageService) {
        this._storageService = storageService;
    }


    // UI related
    setContext(key: string, value: boolean) {
        console.log('Setting context', key, value)
        this.context[key] = value;
    }

    get appViewState(): WebAppState {
        if (!this._appViewState) {
            throw Error('WebAppState not set');
        }
        return this._appViewState;
    }

    setAppViewState(state: WebAppState) {
        if (this._appViewState) {
            // Set appViewState only once to avoid bad reference retention
            // e.g. in the config update handler subscription
            throw Error('AppViewState already set');
        }
        this._appViewState = state;
    }

    async setupFrontendDomainStore(projectId: string) {
        pamet._frontendDomainStore = new FrontendDomainStore()

        // Load the new project and connect it to the Frontend domain store
        let repoUpdateHandler = (repoUpdate: RepoUpdateData) => {
            // This handler will be called whenever the repo is updated
            pamet.frontendDomainStore!.receiveRepoUpdate(repoUpdate)
        }
        try{
            await pamet.storageService.loadProject(
                projectId, pamet.projectStorageConfig(projectId), repoUpdateHandler)

        } catch (e) {
            log.error('Error loading project', e);
        }

        // Load the entities after loading the repo
        let headState = await pamet.storageService.headState(projectId)
        pamet.frontendDomainStore.loadData(headState);

        appActions.setLocalStorageState(this.appViewState, { available: true });
    }

    async detachFrontendDomainStore(projectId: string) {
        log.info('Detaching FDS for project', projectId);
        let currentProject = this.appViewState.currentProject();

        // Mark the local storage as unavailable
        appActions.setLocalStorageState(pamet.appViewState, { available: false });

        if (!currentProject) {
            log.error('Trying to detach FDS without a project');
            return;
        } else if (currentProject.id !== projectId) {
            log.error('Wrong project id passed for FDS detachment');
            return;
        }

        this._frontendDomainStore = null;
        await this.storageService.unloadProject(currentProject.id).catch(
            (e) => {
                log.error('Error unloading project', e);
            }
        )
    }

    // Model related
    get config(): PametConfigService {
        if (!this._config) {
            throw Error('Config not set');
        }
        return this._config;
    }

    setConfig(config: PametConfigService) {
        this._config = config;
        updateAppStateFromConfig(this.appViewState).catch((e) => {
            log.error('[setConfig] Error updating app state from config', e);
        });
        config.setUpdateHandler(() => {
            log.info('Config updated');
            updateAppStateFromConfig(this.appViewState).catch((e) => {
                log.error('[Config.updateHandler] Error updating app state from config', e);
            });
        });
    }

    projects(): ProjectData[] {
        let userData = this.config.userData;
        if (!userData) {
            throw Error('User data not set');
        }
        return userData.projects;
    }

    project(projectId: string): ProjectData | undefined {
        return this.config.projectData(projectId);
    }

    insertOne(entity: Entity<EntityData>): Change {
        return this.frontendDomainStore.insertOne(entity);
    }

    updateOne(entity: Entity<EntityData>): Change {
        return this.frontendDomainStore.updateOne(entity);
    }

    removeOne(entity: Entity<EntityData>): Change {
        return this.frontendDomainStore.removeOne(entity);
    }

    find(filter: SearchFilter = {}): Generator<Entity<EntityData>> {
        return this.frontendDomainStore.find(filter);
    }

    findOne(filter: SearchFilter): Entity<EntityData> | undefined {
        return this.frontendDomainStore.findOne(filter);
    }

    // Media CRUD methods
    async createMediaItem(blob: Blob, path: string): Promise<MediaItem> {
        const currentProjectId = this.appViewState.currentProjectId;
        if (!currentProjectId) {
            throw new Error('No current project set');
        }

        // Create the MediaItem through the storage service
        // This will handle blob storage, dimension extraction, and hash generation
        const mediaItemData = await this.storageService.addMedia(currentProjectId, blob, path);

        // Reconstruct MediaItem from data (since Comlink serialization strips prototype methods)
        const mediaItem = new MediaItem(mediaItemData);

        // Add to the frontend domain store
        this.insertOne(mediaItem);

        return mediaItem;
    }
}


export function updateViewModelFromDelta(appState: WebAppState, delta: Delta) {
    /**
     * A reducer-like function to map entity changes to ViewStates
     * Will be used synchrously from the facade entity CRUD methods (inside actions)
     * And will be used by the domain store watcher service (responcible for
     * updating the view states after external domain store changes)
     */
    console.log('Applying delta to view states', delta)

    for (let change of delta.changes()) {
        let currentPageVS = appState.currentPageViewState
        if (!currentPageVS) {
            continue
        }

        // If it's the current page
        let currentPageId = currentPageVS.page.id;
        let childVS = currentPageVS.viewStateForElementId(change.entityId)
        if (currentPageId === change.entityId) {
            if (change.isDelete()) {
                // If current page gets removed - go to the project page
                if (currentPageVS.page.id === change.entityId) {
                    let userId = appState.userId;
                    if (userId === null) {
                        throw Error('No user set');
                    }
                    let projectId = appState.currentProjectId;
                    if (projectId === null) {
                        throw Error('No project set');
                    }
                    let route = new PametRoute();
                    route.userId = userId;
                    route.projectId = projectId;
                    pamet.router.replaceRoute(route);
                }
            }
            else if (change.isUpdate()) {
                // update view state
                currentPageVS.updateFromChange(change);
            }
        } else if (childVS && change.isDelete()) {
            currentPageVS.removeViewStateForElement(childVS.element());
        } else if (childVS && change.isUpdate()) {
            // update view state
            childVS.updateFromChange(change);
        } else if (change.isCreate()) {
            // If it's a new element
            let entity = pamet.findOne({ id: change.entityId });
            if (entity instanceof Note || entity instanceof Arrow) {
                // get current page vs
                if (!currentPageVS || currentPageVS.page.id !== entity.parentId) {
                    // Skip processing if the parent of the element is not open
                    continue;
                }
                currentPageVS.addViewStateForElement(entity);
            }
        }
    }
}

export const pamet = new PametFacade();
