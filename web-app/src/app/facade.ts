import { AppViewState, SaveStatus } from "@/views/AppViewState";
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
import { StorageServiceProxy, StorageConnectionPhase } from "fusion/storage/management/StorageServiceProxy";
import { ProjectStorageConfig } from "fusion/storage/management/ProjectStorageManager";
import { RepoUpdateData } from "fusion/storage/repository/Repository";
import { Router } from "@/services/routing/Router";
import { registerRootActionCompletedHook, setActionExceptionHandler } from "fusion/registries/Action";
import { PametProjectData, ProjectReference } from "@/model/Project";
import { Keybinding, KeybindingService } from "@/services/KeybindingService";
import { FocusManager } from "@/services/FocusManager";
import { Delta } from "fusion/model/Delta";
import { StoreSyncService } from "fusion/storage/sync/StoreSyncService";
import { switchProject } from "@/procedures/app";
import { appActions } from "@/actions/app";
import { replayActions } from "@/actions/replay";
import { PametRoute } from "@/services/routing/PametRoute";
import { pageActions } from "@/actions/page";
import { PageViewState, PageMode } from "@/views/page/PageViewState";
import { NoteViewState } from "@/views/note/NoteViewState";
import { Point2D } from "fusion/primitives/Point2D";
import { RenderProfiler } from "@/app/RenderProfiler";
import { UndoService, UNDO_ACTION_NAME, REDO_ACTION_NAME } from "@/services/undo/UndoService";
import { SearchService } from "@/services/SearchService";
import { AnimationService } from "@/services/AnimationService";
import { ClipboardService } from "@/services/ClipboardService";
import { ChangeHistoryService } from "@/services/ChangeHistoryService";
import { ReplayService, LockableStore } from "@/services/ReplayService";
import folderWarningIconUrl from "@/resources/icons/folder-warning-line.svg";
import folderCloseIconUrl from "@/resources/icons/folder-close-line.svg";
import folderLineIconUrl from "@/resources/icons/folder-line.svg";
import { ThemeManager, ThemePreference, STORAGE_KEY_PREFERENCE } from "@/app/theme";
import { Store } from "fusion/storage/domain-store/BaseStore";

const log = getLogger('facade');
const completedActionsLogger = getLogger('User action completed');

// Make that more specific as the API clears up
export interface PageQueryFilter { [key: string]: any }

export interface StorageStatusIconSet {
    healthyIconUrl: string;
    unsavedIconUrl: string;
    failedIconUrl: string;
    unavailableIconUrl: string;
}

export type ProjectStorageConfigFactory = (
    projectId: string,
    userId: string,
    deviceId: string,
) => ProjectStorageConfig;



function deriveContextFromViewState(facade: PametFacade) {
    let pageVS = facade.appViewState.currentPageViewState;
    if (facade.appViewState.historyPageViewState) {
        facade.setContext('historyVisible', true);
        // If history is visible - do the rest of the checks on it
        pageVS = facade.appViewState.historyPageViewState;
    }

    if (!pageVS) {
        facade.setContext('notesSelected', false);
        facade.setContext('hasSelection', false);
        facade.setContext('noteEditing', false);
        return;
    }
    let hasNotes = false;
    for (const el of pageVS.selectedElementsVS) {
        if (el instanceof NoteViewState) {
            hasNotes = true;
            break;
        }
    }
    facade.setContext('notesSelected', hasNotes);
    facade.setContext('hasSelection', pageVS.selectedElementsVS.size > 0);
    facade.setContext('noteEditing', pageVS.noteEditWindowState !== null);
}

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
    private _storageService: StorageServiceProxy | null = null;
    router: Router = new Router();
    keybindingService: KeybindingService | null = null;
    _focusManager: FocusManager | null = null;
    searchService: SearchService = new SearchService();
    animationService: AnimationService = new AnimationService();
    clipboardService: ClipboardService = new ClipboardService();
    changeHistoryService: ChangeHistoryService = new ChangeHistoryService();
    private _historyStore: LockableStore = new LockableStore(PAMET_INMEMORY_STORE_CONFIG);
    private _replayService: ReplayService | null = null;

    get historyStore(): LockableStore {
        return this._historyStore;
    }

    get replayService(): ReplayService {
        if (!this._replayService) {
            throw new Error('ReplayService not initialized (no project attached)');
        }
        return this._replayService;
    }

    themeManager: ThemeManager = new ThemeManager();
    context: any = {};
    _projectStorageConfigFactory: ProjectStorageConfigFactory | null = null
    _entityProblemCounts: Map<string, { count: number, firstError?: unknown }> = new Map();
    private _storageStatusIconSet: StorageStatusIconSet = {
        healthyIconUrl: folderWarningIconUrl,
        unsavedIconUrl: folderLineIconUrl,
        failedIconUrl: folderWarningIconUrl,
        unavailableIconUrl: folderCloseIconUrl,
    };
    debug = true;
    debugPaintOperations = false;
    lastRenderError: Error | null = null;
    renderErrorCount: number = 0;
    renderProfiler = new RenderProfiler();

    /**
     * Desktop-injected hook called when change history config may have changed.
     * Receives the projectId so the desktop layer can enable/disable the
     * ChangeHistoryService with the proper WebSocket URL.
     * TODO: There's probably a better implementation for that
     */
    onChangeHistoryConfigChanged: ((projectId: string) => void) | null = null;

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
        // and keep full change hystory if enabled (internal check in pushDelta)
        registerRootActionCompletedHook((rootAction) => {
            if (rootAction.issuer !== 'user') {
                return;
            }
            if (!this._projectSyncService) {
                return;
            }
            const phase = this._storageService?.state.connectionPhase;
            if (phase !== 'ready') {
                return;
            }
            const uncommittedDelta = this._projectSyncService.uncommittedDelta;
            this.changeHistoryService.pushDelta(uncommittedDelta.copy());
            this._projectSyncService.saveUncommittedChanges();
        });

        // Register logger to root actions hooks
        registerRootActionCompletedHook((rootAction) => {
            if (rootAction.issuer !== 'user') {
                return;
            }
            completedActionsLogger.info(rootAction.name);
        });

        // Derive context from viewstate after each root action
        registerRootActionCompletedHook(() => {
            deriveContextFromViewState(this);
        });

        // Register action exception handler to clear page mode and alert
        let _handlingException = false;
        setActionExceptionHandler((actionState, error) => {
            log.error(`Action exception in ${actionState.name}:`, error);

            // Clear page mode with recursion guard
            if (!_handlingException) {
                _handlingException = true;
                try {
                    const pageVS = this._appViewState?.currentPageViewState;
                    if (pageVS && pageVS.mode !== PageMode.None) {
                        pageActions.clearMode(pageVS);
                    }
                } catch (e) {
                    log.error('Error clearing page mode after action exception', e);
                } finally {
                    _handlingException = false;
                }
            }

            // Schedule alert with the error
            const errorMsg = error instanceof Error ? error.message : String(error);
            setTimeout(() => {
                alert(`Action error in ${actionState.name}:\n${errorMsg}`);
            }, 0);
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
    setStorageService(storageService: StorageServiceProxy) {
        this._storageService = storageService;
    }

    setStorageStatusIconSet(iconSet: StorageStatusIconSet) {
        this._storageStatusIconSet = iconSet;
    }

    get storageStatusIconSet(): StorageStatusIconSet {
        return this._storageStatusIconSet;
    }

    getStorageStatusIconUrl(connectionPhase: StorageConnectionPhase, degraded: boolean = false, saveStatus: SaveStatus = 'saved'): string {
        if (connectionPhase === 'fatal' || connectionPhase === 'disconnected' || degraded) {
            return this._storageStatusIconSet.failedIconUrl;
        }
        if (connectionPhase === 'uninitialized' || connectionPhase === 'connecting') {
            return this._storageStatusIconSet.unavailableIconUrl;
        }
        if (saveStatus === 'unsaved' || saveStatus === 'saving') {
            return this._storageStatusIconSet.unsavedIconUrl;
        }
        if (saveStatus === 'error') {
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
        this.context[key] = value;
    }

    contextConditionFulfilled(whenExpression: string): boolean {
        if (whenExpression.includes('==')) {
            throw new Error('== not implemented yet');
        }
        const expr = whenExpression.trim();
        if (expr === '') {
            return true;
        }
        // Disjunction (||) has lower precedence than conjunction (&&)
        const orClauses = expr.split('||').map(c => c.trim()).filter(c => c.length > 0);
        for (const clause of orClauses) {
            if (this._evaluateConjunction(clause)) {
                return true;
            }
        }
        return false;
    }

    private _evaluateConjunction(clause: string): boolean {
        const parts = clause.split('&&').map(p => p.trim()).filter(p => p.length > 0);
        for (const part of parts) {
            let key = part;
            let negate = false;
            if (key.startsWith('!')) {
                negate = true;
                key = key.slice(1).trim();
            }
            const contextVal = this.context[key];
            const partResult = contextVal === true;
            if ((negate ? !partResult : partResult) === false) {
                return false;
            }
        }
        return true;
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
        this._historyStore.onChanges = (delta: Delta) => historyEntityDeltaToViewModelReducer(this.appViewState, delta, this._historyStore);
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
            if (pageId) {
                appActions.applyPageRefCorrections(appViewState, pageId);
            }
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

    // --- Clipboard coordination -----------------------------------------------

    /** Initialize the clipboard service: load persisted data and wire cross-tab sync. */
    initClipboard() {
        const state = this.appViewState;

        // Load persisted clipboard
        const initial = this.clipboardService.getInternalClipboard();
        if (initial.entities.length > 0) {
            appActions.setClipboard(state, initial.entities, initial.projectId);
        }

        // Wire handler for cross-tab updates
        this.clipboardService.setRemoteUpdateHandler((data) => {
            appActions.setClipboard(state, data.entities, data.projectId);
        });

        this.clipboardService.connectListener();
    }

    setClipboard(entities: (Note | Arrow)[], projectId: string | null) {
        appActions.setClipboard(this.appViewState, entities, projectId);
        this.clipboardService.setInternalClipboard({ entities, projectId });
    }

    async attachProjectAsCurrent(projectId: string) {
        // Reset undo histories when switching projects
        this.undoService.clearAll();

        // Create the plain store and wire the view model reducer + change tracking to onChanges
        const store = new InMemoryStore(PAMET_INMEMORY_STORE_CONFIG);
        store.onChanges = (delta, origin) => {
            entityDeltaToViewModelReducer(this.appViewState, delta, store);
            syncService.trackDelta(delta, origin);

            // Mark history replay index as stale (deferred to avoid action-in-action loops)
            const replayVS = this._appViewState?.replayPanelVS;
            if (replayVS?.indexedProjectId && !replayVS.indexStale) {
                setTimeout(() => replayActions.setReplayIndexStale(replayVS, true), 0);
            }
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

        // Enable change history if configured
        this.onChangeHistoryConfigChanged?.(projectId);

        // Create the replay service for this project
        const baseUrl = (window as any).PAMET_DESKTOP_API_BASE_URL;
        const token = (window as any).PAMET_DESKTOP_ACCESS_TOKEN;
        if (baseUrl && token) {
            const historyPathPrefix = `/desktop/projects/${encodeURIComponent(projectId)}/changes/history`;
            this._replayService = new ReplayService(
                this._historyStore,
                historyPathPrefix,
                'main',
                baseUrl,
                { type: 'Bearer', token },
            );
        }
    }

    async detachFromProject(projectId: string) {
        log.info('Detaching from project', projectId);
        this.undoService.clearAll();
        this.searchService.clear();
        this.changeHistoryService.disable();
        if (this._replayService) {
            this._replayService.clear();
            this._replayService = null;
        }

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
            this._configUpdateReaction(delta);
        };

        this._appConfigStore = store;
    }

    private _configUpdateReaction(delta: Delta) {
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

                // Apply theme preference from config store
                const pref = this.userSettings.themePreference ?? ThemePreference.Auto;
                const resolved = this.themeManager.resolveMode(pref);
                appActions.applyTheme(state, pref, resolved);
                localStorage.setItem(STORAGE_KEY_PREFERENCE, pref); // splash hint

                // Re-apply canvas palette for the (possibly new) theme mode
                const currentProjId = state.currentProjectId;
                if (currentProjId) {
                    const projProps = this.loadProjectProperties(currentProjId);
                    appActions.applyCanvasPalette(projProps?.canvas_palette?.[resolved] ?? null);
                }

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

                        // React to record_all_changes toggle
                        this.onChangeHistoryConfigChanged?.(currentId);

                        // Apply canvas palette from project properties
                        const palette = props?.canvas_palette;
                        const mode = this.themeManager.resolvedMode;
                        appActions.applyCanvasPalette(palette?.[mode] ?? null);
                    }
                }
            }
        }
    }

    // UserSettings accessors
    get userSettings(): UserSettings {
        const entity = this.appConfigStore.findOne({ id: UserSettings.SINGLETON_ID });
        if (!entity) {
            throw Error('UserSettings not present in config store');
        }
        return entity as UserSettings;
    }

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

    setThemePreference(pref: ThemePreference): void {
        const us = this.userSettings;
        us.themePreference = pref;
        this.appConfigStore.updateOne(us);
    }

    /**
     * Initialize theme system: sets up media query + DOM reaction, then applies
     * an initial theme from the localStorage hint (pre-config-store).
     * Call once after setAppViewState, before render.
     */
    initializeTheme(): void {
        let pref: ThemePreference = ThemePreference.Auto;
        const stored = localStorage.getItem(STORAGE_KEY_PREFERENCE);
        if (stored === ThemePreference.Light || stored === ThemePreference.Dark || stored === ThemePreference.Auto) {
            pref = stored;
        }
        this.themeManager.initialize(pref);
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
            log.info('[loadProjectProperties] trackedProject NOT found for', projectId);
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
                canvas_palette: pp.canvasPalette,
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
            pp.canvasPalette = projectData.canvas_palette;
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
                canvas_palette: projectData.canvas_palette,
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


export interface ReducerOptions {
    /** When true, skip navigation on page deletion and search index updates. */
    readonly?: boolean;
}

export function entityDeltaToViewModelReducer(
    appViewState: AppViewState,
    delta: Delta,
    store: Store
) {
    /**
     * A reducer-like function to map entity changes to ViewStates upon root action completion
     */
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
                appViewState.currentPageId = null;
                alert('The page you were working on has been deleted (in another tab or manually from storage?).');
                continue;
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
            const element = store.findOne({ id: change.entityId, parentId: currentPageId });
            if (element) {
                // log.info('Adding view state for element', change.entityId, delta);
                currentPageVS.addViewStateForElement(element as Note | Arrow);
            }
        }
    }
}

export function historyEntityDeltaToViewModelReducer(
    appViewState: AppViewState,
    delta: Delta,
    store: Store
) {
    // Updates the history page view state based on history store changes
    let currentPageVS = appViewState.historyPageViewState
    if (currentPageVS === null) {
        // Expected during replay page transitions (PVS hidden before seek)
        return;
    }

    for (let change of delta.changes()) {
        // If it's the current page
        let historyPVS = currentPageVS.page().id;
        if (historyPVS === change.entityId) { // If it's a change of the entity of the currently opened page
            if (change.isDelete() || change.isCreate()){
                // ignore and hope for the best (it's an edge case with an undo/redo or faulty migration)
                continue;
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
            const element = store.findOne({ id: change.entityId, parentId: historyPVS });
            if (element) {
                // log.info('Adding view state for element', change.entityId, delta);
                currentPageVS.addViewStateForElement(element as Note | Arrow);
            }
        }
    }
}

export const pamet = new PametFacade();
