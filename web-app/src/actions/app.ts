import { AppDialogMode, PageError, ProjectError, WebAppState } from "../containers/app/WebAppState";
import { SystemModalDialogState } from "../components/system-modal-dialog/state";
import type { LocalStorageState } from "../containers/app/WebAppState";
import { pamet } from "../core/facade";
import { getLogger } from "fusion/logging";
import { action } from "fusion/libs/Action";
import { PageViewState } from "../components/page/PageViewState";
import type { ProjectData } from "../model/config/Project";
import { currentTime, timestamp } from "fusion/util";
import { deleteProjectAndSwitch } from "../procedures/app";

let log = getLogger("WebAppActions");

class AppActions {
    @action
    setCurrentPage(state: WebAppState, pageId: string) {
        log.info(`Setting current page to ${pageId}`);

        let page = pamet.page(pageId);
        if (page) {
            state.currentPageId = pageId;
            state.currentPageViewState = new PageViewState(page);
            state.currentPageViewState.createElementViewStates();
            state.pageError = PageError.NoError;
        } else {
            console.log("Page not found. FDS:", pamet.frontendDomainStore)
            log.error('Page not found in the domain store.', pageId)
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
    createDefaultProject(): ProjectData {
        const userData = pamet.config.userData;
        if (!userData) {
            throw new Error("User data not found");
        }
        if (userData.projects && userData.projects.length > 0) {
            throw new Error("Cannot create default project: projects already exist");
        }

        const project: ProjectData = {
            id: 'notebook',
            title: "Notebook",
            owner: userData.id,
            description: 'Default project',
            created: timestamp(currentTime())
        };

        userData.projects = [project];
        pamet.config.userData = userData;

        log.info("Created default project", project);
        return project;
    }

    @action
    createProject(project: ProjectData) {
        pamet.config.addProject(project);
    }

    @action
    startProjectDeletionProcedure(project: ProjectData) {
        deleteProjectAndSwitch(project).catch((e) => {
            log.error("Error in startProjectDeletionProcedure", e);
        });
    }

    @action
    updateSystemDialogState(appState: WebAppState, dialogState: SystemModalDialogState | null) {
        appState.systemModalDialogState = dialogState;
    }
}

export const appActions = new AppActions();
