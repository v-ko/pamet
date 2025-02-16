import { AppDialogMode, PageError, ProjectError, WebAppState } from "../containers/app/App";
import type { LocalStorageState } from "../containers/app/App";
import { pamet } from "../core/facade";
import { getLogger } from "fusion/logging";
import { action } from "fusion/libs/Action";
import { PageViewState } from "../components/page/PageViewState";
import type { ProjectData } from "../model/config/Project";
import type { UserData } from "../model/config/User";
import { currentTime, timestamp } from "fusion/util";
import { PametRoute } from "../services/routing/route";

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
        log.info('Setting projectId in view state', projectData ? projectData.id : null);
        state.currentProjectId = projectData ? projectData.id : null;
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

    async deleteProjectAndSwitch(project: ProjectData) {
        // call the async local data erase, then remove the project from the config
        // then if deleting the currently open project
        // switch to another project (if none present - create a default one)
        log.info("Starting delete procedure for project", project);

        // Get projects, return error if the project is missing
        let projects = pamet.projects();
        if (!projects.find(p => p.id === project.id)) {
            throw new Error(`Project with ID ${project.id} not found`);
        }

        // If the project to be deleted is the currently open one
        // set the current project to null
        if (pamet.appViewState.currentProjectId === project.id) {
            log.info("Setting current project to null");
            await pamet.switchToProject(null);
        }

        // Do the requested delete from the local config and storage backend
        log.info("Removing project from config and indexeddb", project);
        pamet.config.removeProject(project.id);
        await pamet.storageService.deleteProject(project.id, pamet.projectManagerConfig(project.id));

        // If there's no projects left, create a default one
        if (pamet.projects().length === 0) {
            log.info("No projects left - creating a default one");
            pamet.config.addProject(appActions.createDefaultProject());
        }

        // If the current project is null (i.e. we've deleted the current project)
        // Use the auto-assist to switch to the first project in the list
        // and create default page if needed, etc
        if (pamet.appViewState.currentProjectId === null) {
            await pamet.router.reachRouteOrAutoassist(new PametRoute());
        }

        log.info("Project deletion procedure completed");
    }

    @action
    startProjectDeletionProcedure(project: ProjectData) {
        this.deleteProjectAndSwitch(project).catch((e) => {
            log.error("Error in startProjectDeletionProcedure", e);
        });
    }
}

export const appActions = new AppActions();
