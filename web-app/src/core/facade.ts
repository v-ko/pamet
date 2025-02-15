import { ProjectError, WebAppState } from "../containers/app/App";
import { getLogger } from 'fusion/logging';
import { SearchFilter } from 'fusion/storage/BaseStore';
import { Change } from "fusion/Change";
import { PametStore } from "../storage/PametStore";
import { Entity, EntityData } from "fusion/libs/Entity";
import { ApiClient } from "../storage/ApiClient";
import { appActions } from "../actions/app";
import { Note } from "../model/Note";
import { Arrow } from "../model/Arrow";
import { FrontendDomainStore } from "../storage/FrontendDomainStore";
import { PametConfigService } from "../services/config/Config";
import { StorageService } from "../storage/StorageService";
import { StorageAdapterNames, ProjectStorageConfig } from "../storage/ProjectStorageManager";
import { RepoUpdateData } from "fusion/storage/BaseRepository";
import { RoutingService } from "../services/routing/RoutingService";
import { PametRoute } from "../services/routing/route";
import { registerRootActionCompletedHook } from "fusion/libs/Action";
import { ProjectData } from "../model/config/Project";
import { KeybindingService } from "../services/KeybindingService";
import { commands } from "./commands";
import { FocusManager } from "../services/FocusManager";
import { Delta } from "fusion/storage/Delta";

const log = getLogger('facade');
const completedActionsLogger = getLogger('User action completed');

// Make that more specific as the API clears up
export interface PageQueryFilter { [key: string]: any }



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
    // Focus handling (context related): Except when receiving focus/blur
    // events - the context change should be applied in the unmount hook
    // (callback returned by useEffect)

    constructor() {
        super()
        this._apiClient = new ApiClient('http://localhost', 3333, '', true);

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

    setContext(key: string, value: boolean) {
        console.log('Setting context', key, value)
        this.context[key] = value;
    }

    projectScopedUrlToGlobal(url: string): string {
        let route = PametRoute.fromUrl(url);
        if (!route.isInternal) {
            throw Error('Url is not internal: ' + url)
        }
        return this._apiClient.endpointUrl(route.path());
    }

    get frontendDomainStore(): FrontendDomainStore {
        if (!this._frontendDomainStore) {
            throw Error('Frontend domain store not set');
        }
        return this._frontendDomainStore;
    }

    setConfig(config: PametConfigService) {
        this._config = config;
        appActions.updateAppStateFromConfig(this.appViewState);
        config.setUpdateHandler(() => {
            appActions.updateAppStateFromConfig(this.appViewState);
        });
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

    get config(): PametConfigService {
        if (!this._config) {
            throw Error('Config not set');
        }
        return this._config;
    }

    apiClient() {
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

    async setCurrentProject(projectId: string | null): Promise<void> {
        // Load the project storage manager in the storage service
        // Swap out the frontend domain store (+ initial state) and connect
        // it to the storage manager (auto-save, confirm save, get remote commits)

        let device = this.config.deviceData;
        const appState = this.appViewState;

        if (!device) {
            throw Error('Device not set');
        }

        if (appState.currentProject) {
            // Check if a change is needed at all
            if (appState.currentProject.id === projectId) {
                return;
            }
            // Else start the process of swapping the project

            // Unload the last project
            log.info('Unloading project', appState.currentProject.id);
            this._frontendDomainStore = null
            await pamet.storageService.unloadProject(appState.currentProject.id);
        }

        // Mark the local storage as unavailable
        appActions.setLocalStorageState(appState, { available: false });

        // let repoManagerConfig: ProjectStorageConfig = {
        //     currentBranchName: device.id,
        //     storageAdapterConfig: {
        //         name: 'InMemory' as StorageAdapterNames, // I really want to remove this cast
        //         args: {
        //             defaultBranchName: device.id, // For testing purposes
        //         }
        //     }
        // }

        let repoManagerConfig: ProjectStorageConfig = {
            currentBranchName: device.id,
            storageAdapterConfig: {
                name: 'IndexedDB' as StorageAdapterNames, // I really want to remove this cast
                args: {
                    defaultBranchName: device.id, // For testing purposes
                }
            }
        }

        if (projectId === null) {
            appActions.setCurrentProject(pamet.appViewState, null);
            return;
        }

        log.info('Loading project', projectId);
        let domainStore = new FrontendDomainStore()
        this._frontendDomainStore = domainStore;

        // Repo update handler
        let repoUpdateHandler = (repoUpdate: RepoUpdateData) => {
            // This handler will be called whenever the repo is updated
            domainStore.receiveRepoUpdate(repoUpdate)
        }

        // Load the new project and connect it to the Frontend domain store
        await this.storageService.loadProject(projectId, repoManagerConfig, repoUpdateHandler)
        // Load the entities after loading the repo
        let headState = await this.storageService.headState(projectId)
        this._frontendDomainStore.loadData(headState);

        appActions.setLocalStorageState(appState, { available: true });

        try {
            let projectData = this.project(projectId);
            appActions.setCurrentProject(appState, projectData);
        } catch (e) {
            appActions.setCurrentProject(appState, null, ProjectError.NotFound);
        }
    }

    projects(): ProjectData[] {
        let userData = this.config.userData;
        if (!userData) {
            throw Error('User data not set');
        }
        return userData.projects;
    }

    project(projectId: string): ProjectData {
        return this.config.projectData(projectId);
    }
    currentProject() {
        return this.appViewState.currentProject;
    }
    updateProject(projectData: ProjectData) {
        // Update in the config
        this.config.updateProjectData(projectData);

        // If it's the current one - update in the appViewState
        let currentProject = this.appViewState.currentProject;
        if (currentProject && currentProject.id === projectData.id) {
            appActions.setCurrentProject(this.appViewState, projectData);
        }
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
                    let projectId = appState.currentProjectId;
                    if (projectId === null) {
                        throw Error('No project set');
                    }
                    let route = new PametRoute();
                    route.projectId = projectId;
                    pamet.router.setRoute(route);
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
