import { ProjectError, WebAppState } from "../containers/app/App";
import { getLogger } from 'pyfusion/logging';
import { Store, SearchFilter } from 'pyfusion/storage/BaseStore';
import { Change } from "pyfusion/Change";
import { PametStore } from "../storage/PametStore";
import { Entity, EntityData } from "pyfusion/libs/Entity";
import { ApiClient } from "../storage/ApiClient";
import { Page } from "../model/Page";
import { appActions } from "../actions/app";
import { Note } from "../model/Note";
import { Arrow } from "../model/Arrow";
import { FrontendDomainStore } from "../storage/FrontendDomainStore";
import { PametConfig } from "../config/Config";
import { StorageService, StorageServiceActualInterface } from "../storage/StorageService";
import { StorageAdapterNames, ProjectStorageConfig } from "../storage/ProjectStorageManager";
import { RepoUpdate } from "../../../fusion/js-src/src/storage/BaseRepository";
import { RoutingService } from "../services/RoutingService";
import { registerRootActionCompletedHook } from "pyfusion/libs/Action";
import { ProjectData } from "../model/config/Project";

const log = getLogger('facade');

// Make that more specific as the API clears up
export interface PageQueryFilter { [key: string]: any }



export class PametFacade extends PametStore {
    private _frontendDomainStore: FrontendDomainStore | null = null;
    private _apiClient: ApiClient;
    private _appViewState: WebAppState | null = null;
    private _changeBufferForRootAction: Array<Change> = [];
    private _config: PametConfig | null = null;
    private _storageService: StorageService | null = null;
    private _projectManagerSubscriptionId: number | null = null;
    router: RoutingService = new RoutingService();

    constructor() {
        super()
        this._apiClient = new ApiClient('http://localhost', 3333, '', true);

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
    }

    pametSchemaToHttpUrl(url: string): string {
        if (!url.startsWith('pamet:')) {
            throw Error('Invalid media url: ' + url)
        }
        url = url.slice('pamet:'.length);
        return this._apiClient.endpointUrl(url);
    }

    get frontendDomainStore(): FrontendDomainStore {
        if (!this._frontendDomainStore) {
            throw Error('Frontend domain store not set');
        }
        return this._frontendDomainStore;
    }

    setConfig(config: PametConfig) {
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

    get config(): PametConfig {
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
        let repoUpdateHandler = (repoUpdate: RepoUpdate) => {
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
            appActions.setCurrentProject(appState, null, ProjectError.NOT_FOUND);
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


export function updateViewModelFromChanges(appState: WebAppState, changes: Array<Change>) {
    /**
     * A reducer-like function to map entity changes to ViewStates
     * Will be used synchrously from the facade entity CRUD methods (inside actions)
     * And will be used by the domain store watcher service (responcible for
     * updating the view states after external domain store changes)
     */
    console.log('Applying changes to view states', changes)
    for (let change of changes) {
        // if page
        let entity = change.lastState;

        let currentPageVS = appState.currentPageViewState
        if (!currentPageVS) {
            continue
        }

        if (entity instanceof Page) {


            // if (change.isCreate()) // pass
            if (change.isDelete()) {
                // remove

                // If current is removed - go to the project

                if (currentPageVS.page.id === entity.id) {
                    let projectId = appState.currentProjectId;
                    if (projectId === null) {
                        throw Error('No project set');
                    }
                    pamet.router.setRoute({ projectId: projectId });
                }
            }
            else if (change.isUpdate()) {
                // update data
                currentPageVS.updateFromPage(entity);
            }
        }
        else if (entity instanceof Note || entity instanceof Arrow) {
            // get current page vs
            if (!currentPageVS || currentPageVS.page.id !== entity.parentId) {
                // Skip processing if the parent of the element is not open
                continue;
            }

            if (change.isCreate()) {
                currentPageVS.addViewStateForElement(entity);
            } else if (change.isDelete()) {
                currentPageVS.removeViewStateForElement(entity);
            }
            else if (change.isUpdate()) {
                currentPageVS.updateEVS_fromElement(entity);
            }
        }
    }
}

export const pamet = new PametFacade();
