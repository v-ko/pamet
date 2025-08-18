import { WebAppState } from "@/containers/app/WebAppState";
import { getLogger } from 'fusion/logging';
import { Change } from "fusion/model/Change";
import { PAMET_INMEMORY_STORE_CONFIG, PametSearchFilter, PametStore } from "@/storage/PametStore";
import { Entity, EntityData } from "fusion/model/Entity";
import { appActions } from "@/actions/app";
import { Note } from "@/model/Note";
import { Arrow } from "@/model/Arrow";
import { MediaItem } from "fusion/model/MediaItem";
import { FrontendDomainStore } from "@/storage/FrontendDomainStore";
import { PametConfigService } from "@/services/config/Config";
import { StorageService } from "fusion/storage/management/StorageService";
import { MediaStoreAdapterNames, ProjectStorageConfig } from "fusion/storage/management/ProjectStorageManager";
import { RepoUpdateData, StorageAdapterNames } from "fusion/storage/repository/Repository";
import { RoutingService } from "@/services/routing/RoutingService";
import { PametRoute } from "@/services/routing/route";
import { registerRootActionCompletedHook } from "fusion/registries/Action";
import { ProjectData } from "@/model/config/Project";
import { Keybinding, KeybindingService } from "@/services/KeybindingService";
import { FocusManager } from "@/services/FocusManager";
import { Delta } from "fusion/model/Delta";
import { updateAppStateFromConfig } from "@/procedures/app";

const log = getLogger('facade');
const completedActionsLogger = getLogger('User action completed');

// Make that more specific as the API clears up
export interface PageQueryFilter { [key: string]: any }



// Service related
export function webStorageConfigFactory(projectId: string): ProjectStorageConfig {
    let device = pamet.config.getDeviceData();
    if (!device) {
        throw Error('Device not set');
    }
    return {
        deviceBranchName: device.id,
        storeIndexConfigs: PAMET_INMEMORY_STORE_CONFIG,
        onDeviceStorageAdapter: {
            name: 'IndexedDB' as StorageAdapterNames,
            args: {
                projectId: projectId,
                localBranchName: device.id,
            }
        },
        onDeviceMediaStore: {
            name: 'CacheAPI' as MediaStoreAdapterNames,
            args: {
                projectId: projectId
            }
        }
    }
}

class RenderProfiler {
    mouseMoveTime?: number;
    renderIds: Set<number> = new Set();
    // mouseMoveEventCounts: number = 0;

    reactRender?: number;
    reactRenderCounts: number = 0;

    mobxReaction?: number;
    mobxReactionCounts: number = 0;

    directRendererInvoke?: number;
    directRendererInvokeCounts: number = 0;

    propSetSkips: number = 0;

    constructor() {
        // clear
    }

    addRenderId(renderId: number) {
        // if (this.mouseMoveTime || !renderId) {
        //     this.propSetSkips++;
        //     return;
        // }
        if (!this.mouseMoveTime) {
            this.mouseMoveTime = performance.now();
            // log.info('Starting render with id:', renderId);
        }
        // log.info(`Render id added: ${renderId}.`);
        this.renderIds.add(renderId);
    }
    setReactRender(renderId: number) {
        this.reactRenderCounts++;
        if (renderId && this.renderIds?.has(renderId)) {
            this.propSetSkips++;
        }
        this.reactRender = performance.now();
    }
    setMobxReaction(renderId: number) {
        this.mobxReactionCounts++;
        if (renderId && this.renderIds?.has(renderId)) {
            this.propSetSkips++;
        }
        this.mobxReaction = performance.now();
    }
    setDirectRendererInvoke(renderId: number) {
        this.directRendererInvokeCounts++;
        if (renderId && this.renderIds?.has(renderId)) {
            this.propSetSkips++;
        }
        this.directRendererInvoke = performance.now();
    }
    logTimeSinceMouseMove(message: string, renderId: number) {
        if (!renderId || !this.renderIds?.has(renderId) || !this.mouseMoveTime) {
            // log.info(`Skipping for request with mouse position ${renderId}.`);
            return;
        }
        let timeSinceMouseMove = performance.now() - this.mouseMoveTime;
        // log.info(`${message} - Time since last mouse move: ${timeSinceMouseMove} ms. Skip count: ${this.propSetSkips}`);
    }

    clear(renderId: number): any {
        // log.info(`Clearing render profiler data. Counts: renderIds.size=${this.renderIds.size}, reactRender=${this.reactRenderCounts}, mobxReaction=${this.mobxReactionCounts}, directRendererInvoke=${this.directRendererInvokeCounts}, propSetSkips=${this.propSetSkips}`);
        if ((!renderId || !this.renderIds?.has(renderId))
            // && !(this.mouseMoveTime && (this.mouseMoveTime + 1000 > performance.now()))
        ) { // if the mouse coordinates are from an e.g. skipped render - timeout and clear
            this.propSetSkips++;
            return;
        }

        let stats = {

        }

        this.mouseMoveTime = undefined;

        this.renderIds.clear()
        this.reactRender = undefined;
        this.reactRenderCounts = 0;

        this.mobxReaction = undefined;
        this.mobxReactionCounts = 0;

        this.directRendererInvoke = undefined;
        this.directRendererInvokeCounts = 0;

        this.propSetSkips = 0;
    }
}

export class PametFacade extends PametStore {
    getEntityId() {
        throw new Error("Method not implemented.");
    }
    private _frontendDomainStore: FrontendDomainStore | null = null;
    private _appViewState: WebAppState | null = null;
    private _config: PametConfigService | null = null;
    private _storageService: StorageService | null = null;
    router: RoutingService = new RoutingService();
    keybindingService: KeybindingService | null = null;
    _focusManager: FocusManager | null = null;
    context: any = {};
    _projectStorageConfigFactory: ((projectId: string) => ProjectStorageConfig) | null = null
    _entityProblemCounts: Map<string, number> = new Map();
    debugging = true;
    debugPaintOperations = true;
    renderProfiler = new RenderProfiler();

    constructor() {
        super()
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
    setKeybindings(keybindings: Keybinding[]) {
        log.info('Setting keybindings', keybindings);
        if (!this.keybindingService) {
            this.keybindingService = new KeybindingService();
        }
        this.keybindingService.setKeybindings(keybindings);
    }

    setupFocusManager() {
        if (this._focusManager) {
            throw Error('Focus manager already set, not setting up again');
        }
        this._focusManager = new FocusManager();
    }
    get focusManager(): FocusManager {
        if (!this._focusManager) {
            throw Error('Focus manager not set up');
        }
        return this._focusManager;
    }

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

    async attachProjectAsCurrent(projectId: string) {
        pamet._frontendDomainStore = new FrontendDomainStore()

        // Load the new project and connect it to the Frontend domain store
        let repoUpdateHandler = (repoUpdate: RepoUpdateData) => {
            // This handler will be called whenever the repo is updated
            pamet.frontendDomainStore!.receiveRepoUpdate(repoUpdate)
        }
        try {
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

    async detachFromProject(projectId: string) {
        log.info('Detaching FDS for project', projectId);
        let currentProject: ProjectData;
        try {
            currentProject = this.appViewState.getCurrentProject();
        } catch (e) {
            log.error('Error getting current project', e);
            return;
        }

        // Mark the local storage as unavailable
        appActions.setLocalStorageState(pamet.appViewState, { available: false });

        this._frontendDomainStore = null;
        await this.storageService.unloadProject(currentProject.id).catch(
            (e) => {
                log.error('Error unloading project', e);
            }
        )

        this._entityProblemCounts.clear();
    }

    reportEntityProblem(entityId: string) {
        this._entityProblemCounts.set(entityId, (this._entityProblemCounts.get(entityId) || 0) + 1);
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
        let userData = this.config.getUserData();
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

    find(filter: PametSearchFilter = {}): Generator<Entity<EntityData>> {
        return this.frontendDomainStore.find(filter);
    }

    findOne(filter: PametSearchFilter): Entity<EntityData> | undefined {
        return this.frontendDomainStore.findOne(filter);
    }

    // Media CRUD methods
    async addMediaToStore(blob: Blob, path: string, parentId: string): Promise<MediaItem> {
        const currentProjectId = this.appViewState.currentProjectId;
        if (!currentProjectId) {
            throw new Error('No current project set');
        }

        // Create the MediaItem through the storage service
        // This will handle blob storage, dimension extraction, and hash generation
        const mediaItemData = await this.storageService.addMedia(currentProjectId, blob, path, parentId);

        return new MediaItem(mediaItemData);
    }
    async deleteMediaFromStore(mediaItem: MediaItem): Promise<void> {
        const currentProjectId = this.appViewState.currentProjectId;
        if (!currentProjectId) {
            throw new Error('No current project set');
        }

        // Remove the media item using the storage service
        await this.storageService.removeMedia(currentProjectId, mediaItem.id, mediaItem.contentHash);
    }
    async moveMediaToTrash(mediaItem: MediaItem): Promise<void> {
        const currentProjectId = this.appViewState.currentProjectId;
        if (!currentProjectId) {
            throw new Error('No current project set');
        }

        // Move the media to trash in the storage service
        await this.storageService.moveMediaToTrash(currentProjectId, mediaItem.id, mediaItem.contentHash);
    }
}


export function entityDeltaToViewModelReducer(appState: WebAppState, delta: Delta) {
    /**
     * A reducer-like function to map entity changes to ViewStates
     * Will be used synchrously from the facade entity CRUD methods (inside actions)
     * And will be used by the domain store watcher service (responcible for
     * updating the view states after external domain store changes)
     *
     *
     */
    // console.log('Applying delta to view states', delta)

    let currentPageVS = appState.currentPageViewState
    if (currentPageVS === null) {
        log.error('No current page view state set, skipping delta', delta);
        return;
    }
    let userId = appState.userId;
    if (userId === null) {
        log.error('No user set, cannot process delta', delta);
        return;
    }

    for (let change of delta.changes()) {
        // If it's the current page
        let currentPageId = currentPageVS.page().id;
        if (currentPageId === change.entityId) { // If it's a change of the entity of the currently opened page
            if (change.isDelete()) {
                // If current page gets removed - go to the project page
                if (currentPageId === change.entityId) {
                    let userId = appState.userId;
                    if (userId === null) {
                        throw Error('No user set');
                    }
                    let projectId = appState.currentProjectId;
                    if (projectId === null) {
                        throw Error('No project set');
                    }
                    let route = new PametRoute({
                        userId: userId,
                        projectId: projectId
                    });
                    pamet.router.replaceRoute(route);
                }
            }
            else if (change.isUpdate()) {
                // update view state
                currentPageVS.updateFromChange(change);
            }
        }

        // Process notes and arrows
        let elementVS = currentPageVS.viewStateForElementId(change.entityId)
        if (elementVS && change.isDelete()) {
            currentPageVS.removeViewStateForElement(elementVS.element() as Note | Arrow);

        } else if (elementVS && change.isUpdate()) {
            elementVS.updateFromChange(change);

        } else if (change.isCreate()) {
            const element = pamet.findOne({ id: change.entityId, parentId: currentPageId }); // Filter only for current page
            if (element) {
                currentPageVS.addViewStateForElement(element as Note | Arrow);
            }
        } else {
            // Change is empty
        }
        // Process media item changes
        let url = currentPageVS.mediaUrlsByItemId.get(change.entityId);
        if (url && change.isDelete()) {
            // Remove the media item from the view state
            currentPageVS.mediaUrlsByItemId.delete(change.entityId);
        } else if (url && change.isUpdate()) {
            // Update the media item URL in the view state
            currentPageVS.mediaUrlsByItemId.set(change.entityId, url);
        } else if (change.isCreate()) {
            // If it's a media item, add it to the view state
            const mediaItem = pamet.mediaItem(change.entityId);
            if (mediaItem) {
                const note = pamet.note(mediaItem?.parentId);
                if (!note) {
                    throw new Error(`Note for media item ${mediaItem.id} not found`);
                }
                if (note?.parentId !== currentPageId) {  // Add only media items for page notes
                    log.info('Skipping media item for note not on current page', note?.parentId, currentPageId);
                    continue;
                }
                currentPageVS.addUrlForMediaItem(mediaItem);
            }
        }

    }
}

export const pamet = new PametFacade();
