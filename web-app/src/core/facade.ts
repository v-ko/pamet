import { WebAppState } from "@/containers/app/WebAppState";
import { getLogger } from 'fusion/logging';
import { Change } from "fusion/model/Change";
import { PametSearchFilter, PametStore } from "@/storage/PametStore";
import { Entity, EntityData } from "fusion/model/Entity";
import { Note } from "@/model/Note";
import { Arrow } from "@/model/Arrow";
import { ImageItem } from "fusion/model/ImageItem";
import { FileItemMetadata } from "fusion/model/FileItem";
import { InMemoryStore } from "fusion/storage/domain-store/InMemoryStore";
import { PAMET_INMEMORY_STORE_CONFIG } from "@/storage/PametStore";
import { OptimisticProjectSyncService } from "@/storage/OptimisticProjectSyncService";
import { UserSettings } from "@/model/config/UserSettings";
import { MiscProperties } from "@/model/config/MiscProperties";
import { ProjectProperties } from "@/model/config/ProjectProperties";
import { StorageService } from "fusion/storage/management/StorageService";
import { ProjectStorageConfig } from "fusion/storage/management/ProjectStorageManager";
import { RepoUpdateData } from "fusion/storage/repository/Repository";
import { RoutingService } from "@/services/routing/RoutingService";
import { registerRootActionCompletedHook } from "fusion/registries/Action";
import { PametProjectData, ProjectReference } from "@/model/Project";
import { Keybinding, KeybindingService } from "@/services/KeybindingService";
import { FocusManager } from "@/services/FocusManager";
import { Delta } from "fusion/model/Delta";
import { StoreSyncClient } from "fusion/storage/sync/StoreSyncClient";
import { switchProject, ensureProjectAndNavigate, applyRoute } from "@/procedures/app";
import { appActions } from "@/actions/app";
import { PametRoute } from "@/services/routing/route";
import { pageActions } from "@/actions/page";
import { PageViewState } from "@/components/page/PageViewState";
import { Point2D } from "fusion/primitives/Point2D";
import { RenderProfiler } from "@/core/RenderProfiler";
import { UndoService, UNDO_ACTION_NAME, REDO_ACTION_NAME } from "@/services/undo/UndoService";
import { SearchService } from "@/services/SearchService";
import { AnimationService } from "@/services/AnimationService";
import folderWarningIconUrl from "@/resources/icons/folder-warning-line.svg";
import folderCloseIconUrl from "@/resources/icons/folder-close-line.svg";
import { StorageConnectionPhase } from "fusion/storage/management/StorageService";

const log = getLogger('facade');
const completedActionsLogger = getLogger('User action completed');

// Make that more specific as the API clears up
export interface PageQueryFilter { [key: string]: any }

export interface StorageStatusIconSet {
    healthyIconUrl: string;
    failedIconUrl: string;
}

export type ProjectStorageConfigFactory = (
    projectId: string,
    userId: string,
    deviceId: string,
) => ProjectStorageConfig;



// Service related
export class PametFacade extends PametStore {
    getEntityId() {
        throw new Error("Method not implemented.");
    }
    clear(): void {
        this.frontendDomainStore.clear();
    }

    _frontendDomainStore: InMemoryStore | null = null;
    private _projectSyncService: OptimisticProjectSyncService | null = null;
    private _appViewState: WebAppState | null = null;
    private _appConfigStore: InMemoryStore | null = null;
    private _storageService: StorageService | null = null;
    router: RoutingService = new RoutingService();
    keybindingService: KeybindingService | null = null;
    _focusManager: FocusManager | null = null;
    searchService: SearchService = new SearchService();
    animationService: AnimationService = new AnimationService();
    context: any = {};
    _projectStorageConfigFactory: ProjectStorageConfigFactory | null = null
    _entityProblemCounts: Map<string, number> = new Map();
    private _storageStatusIconSet: StorageStatusIconSet = {
        healthyIconUrl: folderWarningIconUrl,
        failedIconUrl: folderCloseIconUrl,
    };
    debug = true;
    debugPaintOperations = false;
    renderProfiler = new RenderProfiler();

    undoService: UndoService;

    constructor() {
        super();
        // Initialize UndoService
        this.undoService = new UndoService(this);

        // Register rootAction hook to record user-originated deltas for Undo before saving
        registerRootActionCompletedHook((rootAction) => {
            if (!this._projectSyncService) {
                return;
            }
            if (!rootAction || rootAction.issuer !== 'user') {
                return;
            }
            // Ignore undo/redo actions themselves
            if (rootAction.name === UNDO_ACTION_NAME || rootAction.name === REDO_ACTION_NAME) {
                return;
            }
            const uncommittedDelta = this._projectSyncService.uncommittedDelta;
            if (!uncommittedDelta || uncommittedDelta.isEmpty()) {
                return;
            }
            const currentPageId = this.appViewState.currentPageId;
            if (!currentPageId) {
                log.error('No current page id set, skipping delta record');
                return;
            }
            this.undoService.recordChangeSet(uncommittedDelta, rootAction.name, currentPageId);
        });

        // Register rootAction hook to auto-commit / save
        registerRootActionCompletedHook(() => {
            if (!this._projectSyncService) {
                return;
            }
            this._projectSyncService.saveUncommittedChanges();
        });

        // Register logger to root actions hooks
        registerRootActionCompletedHook((rootAction) => {
            if (rootAction.issuer !== 'user') {
                return;
            }
            completedActionsLogger.info(rootAction.name);
        });
    }

    get projectStorageConfigFactory(): ProjectStorageConfigFactory {
        if (this._projectStorageConfigFactory === null) {
            throw Error('Project storage config factory not set');
        }
        return this._projectStorageConfigFactory;
    }

    setProjectStorageConfigFactory(factory: ProjectStorageConfigFactory) {
        this._projectStorageConfigFactory = factory;
    }

    projectStorageConfig(projectId: string): ProjectStorageConfig {
        const deviceId = this.getDeviceId();
        if (!deviceId) {
            throw Error('Device ID not set');
        }
        const userId = this.appViewState.userId;
        if (!userId) {
            throw Error('User ID not set in app state');
        }
        return this.projectStorageConfigFactory(projectId, userId, deviceId);
    }

    get frontendDomainStore(): InMemoryStore {
        if (!this._frontendDomainStore) {
            throw Error('Frontend domain store not set');
        }
        return this._frontendDomainStore;
    }

    get projectSyncService(): OptimisticProjectSyncService {
        if (!this._projectSyncService) {
            throw Error('Project sync service not set');
        }
        return this._projectSyncService;
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

    setStorageStatusIconSet(iconSet: StorageStatusIconSet) {
        this._storageStatusIconSet = iconSet;
    }

    get storageStatusIconSet(): StorageStatusIconSet {
        return this._storageStatusIconSet;
    }

    getStorageStatusIconUrl(connectionPhase: StorageConnectionPhase): string {
        if (connectionPhase === 'disconnected' || connectionPhase === 'fatal') {
            return this._storageStatusIconSet.failedIconUrl;
        }
        return this._storageStatusIconSet.healthyIconUrl;
    }


    // UI related
    setKeybindings(keybindings: Keybinding[]) {
        log.info('Setting keybindings');
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

    // --- Router coordination --------------------------------------------------

    initRouter() {
        this.router.setUpdateHandler((route) => {
            applyRoute(route).catch((e) => {
                log.error('[Router.updateHandler] Error handling browser route change', e);
            });
        });
        this.router.init();
    }

    /** Push route to URL and derive appState from it. The single entry point for navigation. */
    async navigateTo(route: PametRoute) {
        this.router.navigateToRoute(route);
        await applyRoute(route);
    }

    syncRouterFromAppState() {
        const route = this.appViewState.toRoute();
        this.router.navigateToRoute(route);
    }

    pushNewViewportPosition(state: PageViewState, viewportCenter: Point2D, viewportHeight: number) {
        pageActions.updateViewport(state, viewportCenter, viewportHeight);
        this.syncRouterFromAppState();
    }

    flushRouterFromAppState() {
        const route = this.appViewState.toRoute();
        this.router.flushPendingNavigation(route);
    }

    toggleLastPage() {
        const appState = this.appViewState;
        this.router.toggleLastPage(appState.currentProjectId, appState.currentPageId);
    }

    async attachProjectAsCurrent(projectId: string) {
        // Reset undo histories when switching projects
        this.undoService.clearAll();

        // Create the plain store and wire the view model reducer + change tracking to onChanges
        const store = new InMemoryStore(PAMET_INMEMORY_STORE_CONFIG);
        store.onChanges = (delta, origin) => {
            entityDeltaToViewModelReducer(this.appViewState, delta);
            syncService.trackDelta(delta, origin);
        };

        // Create the sync service (optimistic commit + reconciliation)
        const storageConfig = pamet.projectStorageConfig(projectId);
        const syncService = new OptimisticProjectSyncService(
            store, pamet.storageService, projectId, storageConfig.deviceBranchName
        );

        const trackedProject = this.appViewState.trackedProject(projectId);

        // Load the project in the StorageService, connecting the sync service
        // as the repo-update handler
        let repoUpdateHandler = (repoUpdate: RepoUpdateData) => {
            syncService.receiveRepoUpdate(repoUpdate);
        };
        try {
            await pamet.storageService.loadProject(
                projectId,
                storageConfig,
                repoUpdateHandler,
                trackedProject?.uri,
            );
        } catch (e) {
            log.error('Error loading project', e);
            throw e;
        }

        // Install the store and sync service
        this._frontendDomainStore = store;
        this._projectSyncService = syncService;

        // Hydrate from the storage service
        await syncService.initialize();

        // Initialize search indices with all notes and pages
        const allNotes = Array.from(this.notes());
        const allPages = Array.from(this.pages());
        await this.searchService.initializeIndices(allNotes, allPages);
    }

    async detachFromProject(projectId: string) {
        log.info('Detaching from project', projectId);
        this.undoService.clearAll();
        this.searchService.clear();
        let currentProject: PametProjectData;
        try {
            currentProject = this.appViewState.getCurrentProject();
        } catch (e) {
            log.error('Error getting current project', e);
            return;
        }

        this._frontendDomainStore = null;
        this._projectSyncService = null;
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

    // Config store related
    get appConfigStore(): InMemoryStore {
        if (!this._appConfigStore) {
            throw Error('Config store not set');
        }
        return this._appConfigStore;
    }

    async setupConfigStore(syncService: StoreSyncService) {
        const store = new InMemoryStore();
        syncService.setStore(store);
        await syncService.initialize();

        store.onChanges = (delta, origin) => {
            if (origin !== 'remote') {
                syncService.pushDelta(delta).catch((e) => {
                    log.error('Error pushing config delta to sync service', e);
                });
            }
            this._reduceConfigDelta(delta);
        };

        this._appConfigStore = store;
    }

    /**
     * Reduce a config store delta into app view state updates.
     * Routes by entity ID to update only the affected slice.
     */
    private _reduceConfigDelta(delta: Delta) {
        const state = this.appViewState;
        for (const entityId of delta.entityIds()) {
            if (entityId === MiscProperties.SINGLETON_ID) {
                appActions.applyMiscConfig(
                    state,
                    this.getDeviceId() ?? null,
                    this.getRecentProjects(),
                );

            } else if (entityId === UserSettings.SINGLETON_ID) {
                const userData = this.getUserData();
                appActions.applyUserConfig(
                    state,
                    userData?.id ?? state.userId,
                    this.getTrackedProjectsFromConfig(),
                );

            } else if (entityId.startsWith('project-props-')) {
                // Only care about the current project's properties
                const currentId = state.currentProjectId;
                if (currentId && entityId === ProjectProperties.idForProject(currentId)) {
                    if (!state.trackedProject(currentId)) {
                        // Current project was untracked (deleted in another tab)
                        log.info('Current project removed externally, switching away');
                        alert('The project you were working on has been deleted (in another tab?). Reloading the page.');
                        window.location.reload();
                    } else {
                        const props = this.loadProjectProperties(currentId);
                        appActions.reflectCurrentProjectState(state, props ?? null);
                    }
                }
            }
        }
    }

    // UserSettings accessors
    getUserData(): { id?: string; name?: string; projects?: ProjectReference[] } | undefined {
        const entity = this.appConfigStore.findOne({ id: UserSettings.SINGLETON_ID });
        if (!entity) return undefined;
        const us = entity as UserSettings;
        return { id: us.userId, name: us.userName, projects: us.projects };
    }

    setUserData(userData: { id?: string; name?: string; projects?: ProjectReference[] }): void {
        const existing = this.appConfigStore.findOne({ id: UserSettings.SINGLETON_ID });
        if (existing) {
            const us = existing as UserSettings;
            us.userId = userData.id;
            us.userName = userData.name;
            us.projects = userData.projects ?? [];
            this.appConfigStore.updateOne(us);
        } else {
            const us = new UserSettings({
                id: UserSettings.SINGLETON_ID,
                parent_id: '',
                userId: userData.id,
                userName: userData.name,
                projects: userData.projects ?? [],
            });
            this.appConfigStore.insertOne(us);
        }
    }

    getTrackedProjectsFromConfig(): ProjectReference[] {
        const userData = this.getUserData();
        return userData?.projects ?? [];
    }

    upsertTrackedProject(trackedProject: ProjectReference) {
        const projects = this.getTrackedProjectsFromConfig();
        const index = projects.findIndex((p) => p.id === trackedProject.id);
        if (index === -1) {
            this.setUserData({ ...this.getUserData(), projects: [...projects, trackedProject] });
        } else {
            const next = [...projects];
            next[index] = trackedProject;
            this.setUserData({ ...this.getUserData(), projects: next });
        }
    }

    removeTrackedProject(projectId: string) {
        const projects = this.getTrackedProjectsFromConfig();
        this.setUserData({ ...this.getUserData(), projects: projects.filter((p) => p.id !== projectId) });
    }

    // MiscProperties accessors
    getDeviceId(): string | undefined {
        const entity = this.appConfigStore.findOne({ id: MiscProperties.SINGLETON_ID });
        if (!entity) return undefined;
        const mp = entity as MiscProperties;
        return mp.deviceId;
    }

    setDeviceId(deviceId: string): void {
        const existing = this.appConfigStore.findOne({ id: MiscProperties.SINGLETON_ID });
        if (existing) {
            const mp = existing as MiscProperties;
            mp.deviceId = deviceId;
            this.appConfigStore.updateOne(mp);
        } else {
            const mp = new MiscProperties({
                id: MiscProperties.SINGLETON_ID,
                parent_id: '',
                deviceId: deviceId,
                recentProjects: [],
            });
            this.appConfigStore.insertOne(mp);
        }
    }

    getRecentProjects(): ProjectReference[] {
        const entity = this.appConfigStore.findOne({ id: MiscProperties.SINGLETON_ID });
        if (!entity) return [];
        return (entity as MiscProperties).recentProjects;
    }

    setRecentProjects(projects: ProjectReference[]): void {
        const existing = this.appConfigStore.findOne({ id: MiscProperties.SINGLETON_ID });
        if (existing) {
            const mp = existing as MiscProperties;
            mp.recentProjects = projects;
            this.appConfigStore.updateOne(mp);
        } else {
            const mp = new MiscProperties({
                id: MiscProperties.SINGLETON_ID,
                parent_id: '',
                recentProjects: projects,
            });
            this.appConfigStore.insertOne(mp);
        }
    }

    setMostRecentProject(project: ProjectReference): void {
        const projects = this.getRecentProjects().filter((p) => p.id !== project.id);
        this.setRecentProjects([project, ...projects]);
    }

    removeRecentProject(projectId: string): void {
        const projects = this.getRecentProjects();
        this.setRecentProjects(projects.filter((p) => p.id !== projectId));
    }

    updateRecentProject(projectData: ProjectReference): void {
        const projects = this.getRecentProjects();
        const index = projects.findIndex((p) => p.id === projectData.id);
        if (index === -1) return;
        const next = [...projects];
        next[index] = projectData;
        this.setRecentProjects(next);
    }

    trackedProjects(): ProjectReference[] {
        return this.appViewState.trackedProjects;
    }

    loadProjectProperties(projectId: string): PametProjectData | undefined {
        const trackedProject = this.appViewState.trackedProject(projectId);
        if (!trackedProject) {
            return undefined;
        }
        const propsEntity = this.appConfigStore.findOne({ id: ProjectProperties.idForProject(projectId) });
        if (propsEntity) {
            const pp = propsEntity as ProjectProperties;
            return {
                id: pp.projectId,
                title: pp.title,
                description: pp.description,
                created: pp.created,
                home_page_id: pp.homePageId,
                backups_enabled: pp.backupsEnabled,
            };
        }
        const recentProject = this.recentProject(trackedProject.id);
        return {
            id: trackedProject.id,
            title: trackedProject.title || recentProject?.title || trackedProject.id,
            description: '',
            created: '',
        };
    }

    saveProjectProperties(projectData: PametProjectData): void {
        const entityId = ProjectProperties.idForProject(projectData.id);
        const existing = this.appConfigStore.findOne({ id: entityId });
        if (existing) {
            const pp = existing as ProjectProperties;
            pp.title = projectData.title;
            pp.description = projectData.description;
            pp.homePageId = projectData.home_page_id;
            if (projectData.backups_enabled !== undefined) {
                pp.backupsEnabled = projectData.backups_enabled;
            }
            this.appConfigStore.updateOne(pp);
        } else {
            const pp = new ProjectProperties({
                id: entityId,
                parent_id: '',
                projectId: projectData.id,
                title: projectData.title,
                description: projectData.description,
                created: projectData.created,
                home_page_id: projectData.home_page_id,
                backups_enabled: projectData.backups_enabled,
            });
            this.appConfigStore.insertOne(pp);
        }
        const trackedProject = this.appViewState.trackedProject(projectData.id);
        if (trackedProject) {
            this.upsertTrackedProject({
                ...trackedProject,
                title: projectData.title,
            });
        }
        const recentProject = this.recentProject(projectData.id);
        if (recentProject) {
            this.updateRecentProject({
                id: projectData.id,
                title: projectData.title,
                uri: recentProject.uri,
            });
        }
        if (this.appViewState.currentProjectId === projectData.id) {
            this.appViewState.currentProjectState = projectData;
        }
    }

    recentProjects(): ProjectReference[] {
        return this.appViewState.recentProjects;
    }

    recentProject(projectId: string): ProjectReference | undefined {
        return this.recentProjects().find((project) => project.id === projectId);
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

    // File CRUD methods
    async addFileToStore(blob: Blob, path: string, parentId: string, metadata: FileItemMetadata): Promise<ImageItem> {
        const currentProjectId = this.appViewState.currentProjectId;
        if (!currentProjectId) {
            throw new Error('No current project set');
        }

        // Create the FileItem through the storage service
        // This will handle blob storage and hash generation
        const fileItemData = await this.storageService.addFile(currentProjectId, blob, path, parentId, metadata);

        return new ImageItem(fileItemData);
    }
    async deleteFileFromStore(imageItem: ImageItem): Promise<void> {
        const currentProjectId = this.appViewState.currentProjectId;
        if (!currentProjectId) {
            throw new Error('No current project set');
        }

        // Remove the file item using the storage service
        await this.storageService.removeFile(currentProjectId, imageItem.id, imageItem.contentHash);
    }

    applyDelta(delta: Delta, origin?: string, skipIrrationalOperations: boolean = false): Delta {
        // onChange fires once for the whole batch via applyDelta
        return this.frontendDomainStore.applyDelta(delta, origin, skipIrrationalOperations);
    }
}

/**
 * Updates search indices based on entity changes
 * This is separated from the view model reducer to allow for future refactoring
 */
export function updateSearchIndicesFromDelta(searchService: SearchService, delta: Delta, facade: PametFacade) {
    if (!searchService.isInitialized) {
        return; // Skip if search not initialized
    }

    for (let change of delta.changes()) {
        if (change.isDelete()) {
            // Try to remove from both indices (one will be a no-op)
            searchService.removeNote(change.entityId);
            searchService.removePage(change.entityId);
        } else if (change.isCreate() || change.isUpdate()) {
            // Check if it's a note
            const note = facade.note(change.entityId);
            if (note) {
                if (change.isCreate()) {
                    searchService.addNote(note);
                } else {
                    searchService.updateNote(note);
                }
                continue;
            }

            // Check if it's a page
            const page = facade.page(change.entityId);
            if (page) {
                if (change.isCreate()) {
                    searchService.addPage(page);
                } else {
                    searchService.updatePage(page);
                }
            }
        }
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

    for (let change of delta.changes()) {
        // If it's the current page
        let currentPageId = currentPageVS.page().id;
        if (currentPageId === change.entityId) { // If it's a change of the entity of the currently opened page
            if (change.isDelete()) {
                // If current page gets removed - go to the project page
                if (currentPageId === change.entityId) {
                    let projectId = appState.currentProjectId;
                    if (projectId === null) {
                        throw Error('No project set');
                    }
                    // Current page removed externally: navigate to home page (no auto-creation)
                    const nextPageId = appState.currentProjectState?.home_page_id ?? null;
                    const fallbackRoute = new PametRoute({
                        userId: appState.userId,
                        projectId: projectId,
                        pageId: nextPageId ?? undefined,
                    });
                    pamet.navigateTo(fallbackRoute).catch((e) => {
                        log.error('Error navigating after page deletion in delta reducer', e);
                    });
                    return;
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
            // log.info('Removing view state for element', change.entityId, delta);
            currentPageVS.removeViewStateForElement(elementVS.element() as Note | Arrow);

        } else if (elementVS && change.isUpdate()) {
            // log.info('Updating view state for element', change.entityId, change.data);
            elementVS.updateFromChange(change);

        } else if (change.isCreate()) {
            const element = pamet.findOne({ id: change.entityId, parentId: currentPageId }); // Filter only for current page
            if (element) {
                // log.info('Adding view state for element', change.entityId, delta);
                currentPageVS.addViewStateForElement(element as Note | Arrow);
            }
        }

        // Process image item changes
        const imageItem = pamet.imageItem(change.entityId);
        if (imageItem) {
            if (change.isDelete()) {
                currentPageVS.fileUrlsByItemId.delete(imageItem.id);
            } else {
                // On create/update: always register the URL so notes on the
                // current page can reference it (references may cross pages).
                currentPageVS.addUrlForFileItem(imageItem);
            }
        }
    }

    // Update search indices (separated logic for potential future refactoring)
    try {
        updateSearchIndicesFromDelta(pamet.searchService, delta, pamet);
    } catch (e) {
        log.error('Error while updating search index from delta', e, delta)
    }
}

export const pamet = new PametFacade();
