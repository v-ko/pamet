import { AppDialogMode, PageError, ProjectError, WebAppState } from "../containers/app/App";
import type { LocalStorageState } from "../containers/app/App";
import { pamet } from "../core/facade";
import { getLogger } from "fusion/logging";
import { action } from "fusion/libs/Action";
import { PageViewState } from "../components/page/PageViewState";
import type { ProjectData } from "../model/config/Project";
import type { UserData } from "../model/config/User";
import { currentTime, timestamp } from "fusion/util";

let log = getLogger("WebAppActions");

class AppActions {
    @action
    createDefaultUser(): UserData {
        let userData = pamet.config.userData;

        if (userData) {
             throw Error('Cannot create default user if one already exists')
        }

        userData = {
            id: "user-" + crypto.randomUUID(),
            name: "Anonymous",
            projects: []
        }
        pamet.config.userData = userData;
        return userData
    }

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
            log.error('Page not found in the domain store.')
            state.currentPageId = null;
            state.currentPageViewState = null;
            state.pageError = PageError.NotFound;
        }
        pamet.router.pushRoute(pamet.router.routeFromAppState(state));
    }

    @action
    updateAppStateFromConfig(state: WebAppState) {
        // Device
        let device = pamet.config.deviceData;
        if (device === undefined) {
            state.deviceId = null;
        } else {
            state.deviceId = device.id;
        }

        // User
        let user = pamet.config.userData;
        if (user === undefined) {
            state.userId = null;
        } else {
            state.userId = user.id;
        }

        // Settings?
        // Projects - no , they are in the user config for now
    }

    @action({ issuer: 'service' })
    setLocalStorageState(state: WebAppState, localStorageState: LocalStorageState) {
        // Unload the last project
        state.storageState.localStorage = localStorageState;
    }

    @action
    setCurrentProject(state: WebAppState, projectData: ProjectData | null, projectError: ProjectError = ProjectError.NoError) {
        state.currentProjectId = projectData ? projectData.id : null;
        state.projectError = projectError;
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
    createDefaultProject(): ProjectData {
        const userData = pamet.config.userData;
        if (!userData) {
            throw new Error("User data not found");
        }
        if (userData.projects && userData.projects.length > 0) {
            throw new Error("Cannot create default project: projects already exist");
        }

        const project: ProjectData = {
            id: 'notes',
            name: "Notebook",
            owner: userData.id,
            description: 'Default project',
            created: timestamp(currentTime())
        };

        userData.projects = [project];
        pamet.config.userData = userData;

        return project;
    }

    @action
    addProject(appState: WebAppState, project: ProjectData) {
        pamet.config.addProject(project);
    }

    @action
    deleteProject(project: ProjectData) {
        // Not implemented yet
        throw Error('Project deletion not implemented yet');
    }
}

export const appActions = new AppActions();
