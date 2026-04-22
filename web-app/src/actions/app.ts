import { AppDialogMode, PageError, ProjectError, AppViewState } from "@/views/AppViewState";
import { LoadingDialogState } from "@/views/system-modal-dialog/state";
import type { MouseState } from "@/views/AppViewState";
import { PageAndCommandPaletteState, ProjectPaletteState } from "@/views/CommandPaletteState";
import { LocalSearchViewState } from "@/views/search/LocalSearchViewState";
import { GlobalSearchViewState } from "@/views/search/GlobalSearchViewState";
import { pamet } from "@/app/facade";
import { getLogger } from "fusion/logging";
import { action } from "fusion/registries/Action";
import { PageViewState } from "@/views/page/PageViewState";
import type { PametProjectData, ProjectReference } from "@/model/Project";
import { StorageProxyState } from "fusion/storage/management/StorageServiceProxy";
import type { ThemePreference, ThemeMode } from "@/app/theme";
import { Note } from "@/model/Note";
import { Arrow } from "@/model/Arrow";

let log = getLogger("AppActions");

class AppActions {
    @action
    setCurrentPage(state: AppViewState, pageId: string | null) {
        log.info(`Setting current page to ${pageId}`);

        let page = pageId ? pamet.page(pageId) : null;

        if (page === undefined) {
            log.error('Page not found in the domain store.', pageId)
        }

        if (page) {
            state.currentPageId = pageId;
            let notes = Array.from(pamet.notes({ parentId: pageId }));
            let arrows = Array.from(pamet.arrows({ parentId: pageId }));
            state.currentPageViewState = new PageViewState(page, notes, arrows);

            state.pageError = PageError.NoError;
        } else {
            state.currentPageId = null;
            state.currentPageViewState = null;
            state.pageError = PageError.NotFound;
        }
        // URL synchronization is handled by the RoutingService reaction (State -> URL)
    }

    @action({ issuer: 'service' })
    setStorageServiceState(state: AppViewState, storageServiceState: StorageProxyState) {
        state.storageState.service = storageServiceState;
    }

    @action({ issuer: 'service' })
    reflectCurrentProjectState(state: AppViewState, projectData: PametProjectData | null, projectError: ProjectError = ProjectError.NoError) {
        // This is used only for setting the state. The actual project
        // switching is done in the switchToProject procedure
        log.info('Setting projectId in view state', projectData ? projectData.id : null);
        state.currentProjectId = projectData ? projectData.id : null;
        state.currentProjectState = projectData;
        state.projectError = projectError;
        state.currentPageId = null;
    }

    @action({ issuer: 'service' })
    applyUserConfig(state: AppViewState, userId: string, trackedProjects: ProjectReference[]) {
        state.userId = userId;
        state.trackedProjects = trackedProjects;
    }

    @action({ issuer: 'service' })
    applyDeviceState(state: AppViewState, deviceId: string | null, recentProjects: ProjectReference[]) {
        state.deviceId = deviceId;
        state.recentProjects = recentProjects;
    }

    @action({ issuer: 'service' })
    updateMouseState(state: AppViewState, mouseStateProps: Partial<MouseState>) {
        // Update the mouse state with the given properties
        Object.assign(state.mouseState, mouseStateProps);
    }

    @action
    closeAppDialog(appViewState: AppViewState) {
        appViewState.dialogMode = AppDialogMode.Closed;
    }

    @action
    openPageProperties(appViewState: AppViewState) {
        appViewState.dialogMode = AppDialogMode.PageProperties;
    }

    @action
    openProjectPropertiesDialog(appViewState: AppViewState) {
        appViewState.dialogMode = AppDialogMode.ProjectProperties;
    }

    @action
    openProjectsDialog(appViewState: AppViewState) {
        appViewState.dialogMode = AppDialogMode.ProjectsDialog;
    }

    @action
    openCreateProjectDialog(appViewState: AppViewState) {
        appViewState.dialogMode = AppDialogMode.CreateNewProject;
    }

    @action
    openStorageStatusDialog(appViewState: AppViewState) {
        appViewState.dialogMode = AppDialogMode.StorageStatus;
    }

    @action
    updateSystemDialogState(appViewState: AppViewState, props: Partial<LoadingDialogState> | LoadingDialogState | null) {
        if (appViewState.loadingDialogState === null) {  // Open dialog
            if (props === null) {
                throw new Error("Cannot open loading dialog without props");
            }
            appViewState.loadingDialogState = new LoadingDialogState(props.title || '', props.taskDescription || '', props.taskProgress || -1, props.showAfterUnixTime || 0);
        } else {
            // Update dialog state
            if (props === null) {
                appViewState.loadingDialogState = null; // Close dialog
            } else {
                if (props.title !== undefined) {
                    appViewState.loadingDialogState.title = props.title;
                }
                if (props.taskDescription !== undefined) {
                    appViewState.loadingDialogState.taskDescription = props.taskDescription;
                }
                if (props.taskProgress !== undefined) {
                    appViewState.loadingDialogState.taskProgress = props.taskProgress;
                }
                if (props.showAfterUnixTime !== undefined) {
                    appViewState.loadingDialogState.showAfterUnixTime = props.showAfterUnixTime;
                }
            }
        }
    }

    @action
    openPageAndCommandPalette(appViewState: AppViewState, initialInput: string) {
        appViewState.commandPaletteState = new PageAndCommandPaletteState(initialInput);
    }

    @action
    openProjectPalette(appViewState: AppViewState) {
        appViewState.commandPaletteState = new ProjectPaletteState('');
    }

    @action
    closeCommandPalette(appViewState: AppViewState) {
        appViewState.commandPaletteState = null;
    }

    @action
    openLocalSearch(appViewState: AppViewState, initialQuery: string = '') {
        appViewState.localSearchViewState = new LocalSearchViewState(initialQuery);
    }

    @action
    closeLocalSearch(appViewState: AppViewState) {
        appViewState.localSearchViewState = null;
    }

    @action
    openGlobalSearch(appViewState: AppViewState, initialQuery: string = '') {
        if (appViewState.globalSearchViewState) {
            // If already open, increment focus counter to trigger re-focus
            appViewState.globalSearchViewState.incrementFocusCounter();
        } else {
            // Create new instance if not open
            appViewState.globalSearchViewState = new GlobalSearchViewState(initialQuery);
        }
    }

    @action
    closeGlobalSearch(appViewState: AppViewState) {
        appViewState.globalSearchViewState = null;
    }

    @action
    applyTheme(state: AppViewState, preference: ThemePreference, resolvedMode: ThemeMode) {
        state.themePreference = preference;
        state.themeResolvedMode = resolvedMode;
    }

    @action({ issuer: 'service' })
    setClipboard(state: AppViewState, entities: (Note | Arrow)[], projectId: string | null) {
        state.clipboard = entities;
        state.clipboardProjectId = projectId;
    }
}

export const appActions = new AppActions();
