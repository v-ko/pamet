import { AppDialogMode, PageError, ProjectError, WebAppState } from "@/containers/app/WebAppState";
import { LoadingDialogState } from "@/components/system-modal-dialog/state";
import type { LocalStorageState } from "@/containers/app/WebAppState";
import { PageAndCommandPaletteState, ProjectPaletteState } from "@/components/CommandPaletteState";
import { pamet } from "@/core/facade";
import { getLogger } from "fusion/logging";
import { action } from "fusion/registries/Action";
import { PageViewState } from "@/components/page/PageViewState";
import type { ProjectData } from "@/model/config/Project";
import { Entity } from "fusion/model/Entity";

let log = getLogger("WebAppActions");

class AppActions {
    @action
    setCurrentPage(state: WebAppState, pageId: string | null) {
        log.info(`Setting current page to ${pageId}`);

        let page = pageId ? pamet.page(pageId) : null;
        
        if (page === undefined) {
            log.error('Page not found in the domain store.', pageId)
        }

        if (page) {
            state.currentPageId = pageId;
            state.currentPageViewState = new PageViewState(page);
            state.currentPageViewState.createElementViewStates();
            state.pageError = PageError.NoError;
        } else {
            state.currentPageId = null;
            state.currentPageViewState = null;
            state.pageError = PageError.NotFound;
        }
        pamet.router.pushRoute(state.route());
    }

    @action({ issuer: 'service' })
    setLocalStorageState(state: WebAppState, localStorageState: LocalStorageState) {
        // Unload the last project
        state.storageState.localStorage = localStorageState;
    }

    @action({ issuer: 'service' })
    reflectCurrentProjectState(state: WebAppState, projectData: ProjectData | null, projectError: ProjectError = ProjectError.NoError) {
        // This is used only for setting the state. The actual project
        // switching is done in the switchToProject procedure
        log.info('Setting projectId in view state', projectData ? projectData.id : null);
        state.currentProjectId = projectData ? projectData.id : null;
        state.currentProjectState = projectData;
        state.projectError = projectError;
        state.currentPageId = null;
    }

    @action
    closeAppDialog(appState: WebAppState) {
        appState.dialogMode = AppDialogMode.Closed;
    }

    @action
    openPageProperties(appState: WebAppState) {
        appState.dialogMode = AppDialogMode.PageProperties;
    }

    @action
    openProjectPropertiesDialog(appState: WebAppState) {
        appState.dialogMode = AppDialogMode.ProjectProperties;
    }

    @action
    openProjectsDialog(appState: WebAppState) {
        appState.dialogMode = AppDialogMode.ProjectsDialog;
    }

    @action
    openCreateProjectDialog(appState: WebAppState) {
        appState.dialogMode = AppDialogMode.CreateNewProject;
    }

    @action
    updateSystemDialogState(appState: WebAppState, props: Partial<LoadingDialogState> | LoadingDialogState | null) {
        if (appState.loadingDialogState === null){  // Open dialog
            if (props === null) {
                throw new Error("Cannot open loading dialog without props");
            }
            appState.loadingDialogState = new LoadingDialogState(props.title || '', props.taskDescription || '', props.taskProgress || -1, props.showAfterUnixTime || 0);
        } else {
            // Update dialog state
            if (props === null) {
                appState.loadingDialogState = null; // Close dialog
            } else {
                if (props.title !== undefined) {
                    appState.loadingDialogState.title = props.title;
                }
                if (props.taskDescription !== undefined) {
                    appState.loadingDialogState.taskDescription = props.taskDescription;
                }
                if (props.taskProgress !== undefined) {
                    appState.loadingDialogState.taskProgress = props.taskProgress;
                }
                if (props.showAfterUnixTime !== undefined) {
                    appState.loadingDialogState.showAfterUnixTime = props.showAfterUnixTime;
                }
            }
        }
    }

    @action
    importEntitiesAction(entities: Entity<any>[]) {
        for (const entity of entities) {
            pamet.insertOne(entity);
        }
    }

    @action
    openPageAndCommandPalette(appState: WebAppState, initialInput: string) {
        appState.commandPaletteState = new PageAndCommandPaletteState(initialInput);
    }

    @action
    openProjectPalette(appState: WebAppState) {
        appState.commandPaletteState = new ProjectPaletteState('');
    }

    @action
    closeCommandPalette(appState: WebAppState) {
        appState.commandPaletteState = null;
    }
}

export const appActions = new AppActions();
