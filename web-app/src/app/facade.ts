import { AppViewState } from "@/views/AppViewState";
import { getLogger } from 'fusion/logging';
import { Change } from "fusion/model/Change";
import { PametSearchFilter, PametStore } from "@/storage/PametStore";
import { Entity, EntityData } from "fusion/model/Entity";
import { Note } from "@/model/Note";
import { Arrow } from "@/model/Arrow";
import { InMemoryStore } from "fusion/storage/domain-store/InMemoryStore";
import { PAMET_INMEMORY_STORE_CONFIG } from "@/storage/PametStore";
import { OptimisticProjectSyncService } from "@/storage/OptimisticProjectSyncService";
import { UserSettings } from "@/model/config/UserSettings";
import { DeviceState } from "@/model/config/DeviceState";
import { ProjectProperties } from "@/model/config/ProjectProperties";
import { StorageService } from "fusion/storage/management/StorageService";
import { ProjectStorageConfig } from "fusion/storage/management/ProjectStorageManager";
import { RepoUpdateData } from "fusion/storage/repository/Repository";
import { Router } from "@/services/routing/Router";
import { registerRootActionCompletedHook } from "fusion/registries/Action";
import { PametProjectData, ProjectReference } from "@/model/Project";
import { Keybinding, KeybindingService } from "@/services/KeybindingService";
import { FocusManager } from "@/services/FocusManager";
import { Delta } from "fusion/model/Delta";
import { StoreSyncService } from "fusion/storage/sync/StoreSyncService";
import { switchProject } from "@/procedures/app";
import { appActions } from "@/actions/app";
import { PametRoute } from "@/services/routing/PametRoute";
import { pageActions } from "@/actions/page";
import { PageViewState } from "@/views/page/PageViewState";
import { Point2D } from "fusion/primitives/Point2D";
import { RenderProfiler } from "@/app/RenderProfiler";
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
        this.currentProjectStore.clear();
    }

    _currentProjectStore: InMemoryStore | null = null;
    private _projectSyncService: OptimisticProjectSyncService | null = null;
    private _appViewState: AppViewState | null = null;
    private _appConfigStore: InMemoryStore | null = null;
    private _storageService: StorageService | null = null;
    router: Router = new Router();
    keybindingService: KeybindingService | null = null;
    _focusManager: FocusManager | null = null;
    searchService: SearchService = new SearchService();
    animationService: AnimationService = new AnimationService();
    context: any = {};
    _projectStorageConfigFactory: ProjectStorageConfigFactory | null = null
    _entityProblemCounts: Map<string, { count: number, firstError?: unknown }> = new Map();
    private _storageStatusIconSet: StorageStatusIconSet = {
        healthyIconUrl: folderWarningIconUrl,
        failedIconUrl: folderCloseIconUrl,
    };
    debug = true;
    debugPaintOperations = false;
    lastRenderError: Error | null = null;
    renderErrorCount: number = 0;
    renderProfiler = new RenderProfiler();

    hideSplash() {
        const splash = document.getElementById('splash');
        if (!splash) return;
        splash.classList.add('fade-out');
        setTimeout(() => splash.remove(), 350);
    }

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
            throw Error('User ID not set in app view state');
        }
        return this.projectStorageConfigFactory(projectId, userId, deviceId);
    }

    get currentProjectStore(): InMemoryStore {
        if (!this._currentProjectStore) {
            throw Error('Current project store not set');
        }
        return this._currentProjectStore;
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

    get appViewState(): AppViewState {
        if (!this._appViewState) {
            throw Error('AppViewState not set');
        }
        return this._appViewState;
    }

    setAppViewState(state: AppViewState) {
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
            this.handlePopstateRoute(route);
        });
        this.router.init();
    }

    /**
     * The single entry point for navigation.
     * Switches project if needed, resolves default page, updates URL, then applies state.
     */
    async navigateTo(route: PametRoute, { replace = false }: { replace?: boolean } = {}) {
        const appViewState = this.appViewState;

        // Project switch if needed (async)
        const targetProjectId = route.projectId ?? null;
        if (appViewState.currentProjectId !== targetProjectId) {
            await switchProject(targetProjectId);
        }

        // Resolve default page if not specified
        const pageId = route.pageId
            ?? (appViewState.currentProjectState?.home_page_id ?? null);
        if (!route.pageId && pageId) {
            route = new PametRoute({
                userId: route.userId,
                projectId: route.projectId,
                pageId: pageId,
                viewportCenter: route.viewportCenter,
                viewportEyeHeight: route.viewportEyeHeight,
            });
            replace = true;  // Redirect to default page should not create a history entry
        }

        // Update URL
        if (replace) {
            this.router.replaceRoute(route);
        } else {
            this.router.pushRoute(route);
        }

        // Apply state
        if (pageId !== appViewState.currentPageId) {
            appActions.setCurrentPage(appViewState, pageId);
        }
        if (appViewState.currentPageViewState && route.viewportCenter && route.viewportEyeHeight) {
            const [x, y] = route.viewportCenter;
            pageActions.updateViewport(
                appViewState.currentPageViewState,
                new Point2D([x, y]),
                route.viewportEyeHeight,
            );
        }
    }

    /** Handle a route from popstate (back/forward/toggleLastPage).
     *  The browser has already updated the URL, so we only apply state (replace, not push). */
    private handlePopstateRoute(route: PametRoute) {
        this.navigateTo(route, { replace: true }).catch((e) => {
            log.error('[Router.updateHandler] Error handling browser route change', e);
        });
    }

    updateViewportUrl(state: PageViewState, viewportCenter: Point2D, viewportHeight: number) {
        pageActions.updateViewport(state, viewportCenter, viewportHeight);
        const route = this.appViewState.toRoute();
        this.router.replaceRoute(route, { debounce: true });
    }

    toggleLastPage() {
        const appViewState = this.appViewState;
        this.router.toggleLastPage(appViewState.currentProjectId, appViewState.currentPageId);
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
        this._currentProjectStore = store;
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

        this._currentProjectStore = null;
        this._projectSyncService = null;
        await this.storageService.unloadProject(currentProject.id).catch(
            (e) => {
                log.error('Error unloading project', e);
            }
        )

        this._entityProblemCounts.clear();
        this.lastRenderError = null;
        this.renderErrorCount = 0;
        if (this._appViewState) {
            this._appViewState.devErrors = false;
        }
    }

    reportEntityProblem(entityId: string, error?: unknown) {
        let entry = this._entityProblemCounts.get(entityId);
        if (!entry) {
            entry = { count: 0, firstError: error };
            this._entityProblemCounts.set(entityId, entry);
        }
        entry.count++;
        if (this._appViewState) {
            this._appViewState.devErrors = true;
        }
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
            if (entityId === DeviceState.SINGLETON_ID) {
                appActions.applyDeviceState(
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

    // DeviceState accessors
    getDeviceId(): string | undefined {
        const entity = this.appConfigStore.findOne({ id: DeviceState.SINGLETON_ID });
        if (!entity) return undefined;
        const mp = entity as DeviceState;
        return mp.deviceId;
    }

    setDeviceId(deviceId: string): void {
        const existing = this.appConfigStore.findOne({ id: DeviceState.SINGLETON_ID });
        if (existing) {
            const mp = existing as DeviceState;
            mp.deviceId = deviceId;
            this.appConfigStore.updateOne(mp);
        } else {
            const mp = new DeviceState({
                id: DeviceState.SINGLETON_ID,
                parent_id: '',
                deviceId: deviceId,
                recentProjects: [],
            });
            this.appConfigStore.insertOne(mp);
        }
    }

    getRecentProjects(): ProjectReference[] {
        const entity = this.appConfigStore.findOne({ id: DeviceState.SINGLETON_ID });
        if (!entity) return [];
        return (entity as DeviceState).recentProjects;
    }

    setRecentProjects(projects: ProjectReference[]): void {
        const existing = this.appConfigStore.findOne({ id: DeviceState.SINGLETON_ID });
        if (existing) {
            const mp = existing as DeviceState;
            mp.recentProjects = projects;
            this.appConfigStore.updateOne(mp);
        } else {
            const mp = new DeviceState({
                id: DeviceState.SINGLETON_ID,
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
                project_id: projectData.id,
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
        return this.currentProjectStore.insertOne(entity);
    }

    updateOne(entity: Entity<EntityData>): Change {
        return this.currentProjectStore.updateOne(entity);
    }

    removeOne(entity: Entity<EntityData>): Change {
        return this.currentProjectStore.removeOne(entity);
    }

    find(filter: PametSearchFilter = {}): Generator<Entity<EntityData>> {
        return this.currentProjectStore.find(filter);
    }

    findOne(filter: PametSearchFilter): Entity<EntityData> | undefined {
        return this.currentProjectStore.findOne(filter);
    }

    // File CRUD methods
    async addFile(blob: Blob, path: string): Promise<{ hash: string, path: string }> {
        const currentProjectId = this.appViewState.currentProjectId;
        if (!currentProjectId) {
            throw new Error('No current project set');
        }

        return await this.storageService.addFile(currentProjectId, blob, path);
    }
    async deleteFile(path: string): Promise<void> {
        const currentProjectId = this.appViewState.currentProjectId;
        if (!currentProjectId) {
            throw new Error('No current project set');
        }

        await this.storageService.removeFile(currentProjectId, path);
    }

    applyDelta(delta: Delta, origin?: string, skipIrrationalOperations: boolean = false): Delta {
        // onChange fires once for the whole batch via applyDelta
        return this.currentProjectStore.applyDelta(delta, origin, skipIrrationalOperations);
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


export function entityDeltaToViewModelReducer(appViewState: AppViewState, delta: Delta) {
    /**
     * A reducer-like function to map entity changes to ViewStates
     * Will be used synchrously from the facade entity CRUD methods (inside actions)
     * And will be used by the domain store watcher service (responcible for
     * updating the view states after external domain store changes)
     *
     *
     */
    // console.log('Applying delta to view states', delta)

    let currentPageVS = appViewState.currentPageViewState
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
                    let projectId = appViewState.currentProjectId;
                    if (projectId === null) {
                        throw Error('No project set');
                    }
                    // Current page removed externally: navigate to home page (no auto-creation)
                    const nextPageId = appViewState.currentProjectState?.home_page_id ?? null;
                    const fallbackRoute = new PametRoute({
                        userId: appViewState.userId,
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
    }

    // Update search indices (separated logic for potential future refactoring)
    try {
        updateSearchIndicesFromDelta(pamet.searchService, delta, pamet);
    } catch (e) {
        log.error('Error while updating search index from delta', e, delta)
    }
}

export const pamet = new PametFacade();
