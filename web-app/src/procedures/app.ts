import { getLogger } from "fusion/logging";
import { pamet } from "../core/facade";
import { ProjectData } from "../model/config/Project";
import { appActions } from "../actions/app";
import { PametRoute } from "../services/routing/route";
import { ProjectError, WebAppState } from "../containers/app/App";
import { projectActions } from "../actions/project";
import { Page } from "../model/Page";

const log = getLogger('AppProcedures');


let projectSwithLock = false;

export async function switchToProject(projectId: string | null): Promise<void> {
    // A procedure to switch the storage backend to a new project. This
    //  requires swapping out the frontend domain store and reporting the
    // status of the backend availability to UI

    // Load the project storage manager in the storage service
    // Swap out the frontend domain store (+ initial state) and connect it
    // to the latter (for auto-save, etc.)

    if (projectSwithLock) {
        log.error('Project switch already in progress');
        return;
    }
    projectSwithLock = true;

    const appState = pamet.appViewState;
    let currentProjectId = pamet.appViewState.currentProjectId;
    let idsMatch = currentProjectId === projectId;

    // Setup the logic as flags

    // If there's an FDS setup, and it's not the same as the one we're switching
    // to - detach it
    let shouldDetach = !!currentProjectId && !idsMatch;

    // Check if the project for the id actually exists
    let projectData = projectId ? pamet.project(projectId) : undefined;
    let projectFound = !!projectData;

    // If there's a project id, and the project exists, and it's not the same
    // as the one we're switching to - attach it
    let shouldAttachNew = projectFound && !idsMatch;

    try {
        // Unload the current project if there is one
        // and if it's not the same as the one we're switching to
        if (shouldDetach) {
            await pamet.detachFrontendDomainStore(currentProjectId!);
        }

        if (shouldAttachNew) {
            await pamet.setupFrontendDomainStore(projectData!.id);
        }

        // Reflect the new project state in the app state
        // If we've attached a new project we update the view state
        // If the project is the same - again we update the view state for good measure
        if (shouldAttachNew || (idsMatch && projectData)) {
            appActions.reflectCurrentProjectState(appState, projectData!);

            // If the request is to detach the FDS - reflect that
        } else if (projectId === null) {
            appActions.reflectCurrentProjectState(appState, null);

            // If a request is made to load a project but it's not found, set error
        } else if (projectId !== null && !projectFound) {
            appActions.reflectCurrentProjectState(appState, null, ProjectError.NotFound);
        }

    } finally {
        projectSwithLock = false;
    }
}


export async function deleteProjectAndSwitch(project: ProjectData) {
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
    // we detach
    if (pamet.appViewState.currentProjectId === project.id) {
        log.info("Detaching FDS");
        await switchToProject(null);
    }

    // Ask here, so that there's no chance another tab creates the default
    // project first, creating a conflict
    if (pamet.projects().length === 1) {
        alert('You\'re deleting the last project. A new one will be created.')
    }

    // Do the requested delete from the local config and storage backend
    log.info("Removing project from config and indexeddb", project);

    // Remove from config which will signal the other tabs to unload the project
    pamet.config.removeProject(project.id);

    // Create a timeout promise
    const DELETION_TIMEOUT = 5000; // 5 seconds
    const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
            reject(new Error('Project deletion timed out - other tabs may be blocking'));
        }, DELETION_TIMEOUT);
    });


    let deletionPromise = pamet.storageService.deleteProject(
        project.id,
        pamet.projectManagerConfig(project.id)
    )

    try {
        // Race between deletion and timeout
        await Promise.race([
            deletionPromise,
            timeoutPromise
        ]);

        // If we get here, deletion succeeded before timeout

    } catch (error: any) {
        log.error('Error during project deletion:', error);

        if (error?.message?.includes('timed out')) {
            // If it timed out, show warning and proceed with config removal
            log.error('Project deletion timed out.');
        } else {
            // For other errors, rethrow
            throw error;
        }
    }

    // If there's no projects left, create a default one
    if (pamet.projects().length === 0) {
        log.info("No projects left - creating a default one");
        appActions.createDefaultProject();
    }

    // If the current project is null (i.e. we've deleted the current project)
    // Use the auto-assist to switch to the first project in the list
    // and create default page if needed, etc
    if (pamet.appViewState.currentProjectId === null) {
        await updateAppFromRouteOrAutoassist(new PametRoute());
    }

    log.info("Project deletion procedure completed");
}


export async function updateAppFromRoute(route: PametRoute): Promise<void> {
    // Reflects the route in the app state without any side effects
    log.info('updateAppFromRoute for route', route);

    let projectId = route.projectId;
    // If no project id -
}

export async function updateAppFromRouteOrAutoassist(route: PametRoute): Promise<void> {
    // "Reaches" the route by executing the necessary app configuration
    log.info('updateAppFromRouteOrAutoassist for route', route);

    // If no project id - go to default project (or create one)
    let projectId = route.projectId;
    if (projectId === undefined) {
        // go to default project
        let projects = pamet.projects();
        if (projects.length === 0) {
            log.info('No projects found. Creating a default one');
            appActions.createDefaultProject();
            await updateAppFromRouteOrAutoassist(new PametRoute());
            return;
        } else {
            log.info('Switching to the first project');
            let firstProjectRoute = new PametRoute()
            firstProjectRoute.projectId = projects[0].id;
            await pamet.router.changeRouteAndApplyToApp(firstProjectRoute);
            return;
        }
    }

    // Get project data from config
    let userData = pamet.config.userData;
    if (!userData) {
        throw Error('User data not loaded');
    }

    await switchToProject(projectId); // view state updated here

    let projectData = pamet.project(projectId);

    // If undefined switching will have set the 404 message
    if (!projectData) {
        return;
    }

    // If there's a page id - apply it
    let pageId = route.pageId;
    if (pageId !== undefined) {
        appActions.setCurrentPage(pamet.appViewState, pageId);
    } else {  // If there's no page id
        // Goto first/default page
        let goToPageId: string | undefined = undefined;

        // Check for default page in the project
        if (projectData.defaultPageId) {
            // Check that the page is present
            let page = pamet.findOne({ id: projectData.defaultPageId });
            if (!page) { // If the default page is set, but missing
                log.error('Default page not found in the repo for id', projectData.defaultPageId);
                log.info('Removing default page id from the project')
                // Set defaultPageId to null in the project
                projectData.defaultPageId = undefined;
                projectActions.updateProject(projectData);
            } else {
                log.info('Switching to default page', projectData.defaultPageId);
                goToPageId = projectData.defaultPageId;
            }
        }

        // If no default page is set
        if (!goToPageId) {
            let firstPage = pamet.findOne({ type: Page });
            if (firstPage) {
                log.info('Switching to the first page', firstPage.id);
                goToPageId = firstPage.id;
            } else {  // If no pages present
                // Create a default page
                log.info('No pages found in the project. Creating a default page');
                // TODO: Move that logic to somewhere else
                projectActions.createDefaultPage(pamet.appViewState);
                let newPage = pamet.findOne({ type: Page });
                if (!newPage) {
                    throw Error('Default page not created');
                }
                log.info('Switching to the newly created default page', newPage);
                goToPageId = newPage.id;
            }
        }

        if (goToPageId !== undefined) {
            let defaultPageRoute = new PametRoute();
            defaultPageRoute.projectId = projectId;
            defaultPageRoute.pageId = goToPageId;
            await pamet.router.changeRouteAndApplyToApp(defaultPageRoute);
        } else {
            log.error('Could not find/create a page to go to.');
        }
    }
}



export async function updateAppStateFromConfig(appState: WebAppState) {
    // Device
    let device = pamet.config.deviceData;
    if (device === undefined) {
        appState.deviceId = null;
    } else {
        appState.deviceId = device.id;
    }

    // User
    let user = pamet.config.userData;
    if (user === undefined) {
        appState.userId = null;
    } else {
        appState.userId = user.id;
    }

    // Settings - not yet implemented

    // Projects
    if (appState.currentProjectId) {
        // If the current project has been deleted, reload the page so that
        // the router goes to the default project
        let projects = pamet.projects();
        let currentProjectNewState = projects.find(p => p.id === appState.currentProjectId);
        if (currentProjectNewState === undefined) {
            log.info('Project deleted in other tab.');
            alert('The project you were working on has been deleted in another tab. Reloading the page.');
            window.location.reload();
        } else {
            // Else update the current project data in the app state
            // * This should be implemented as a mobx reaction at some point to avoid
            // redundant updates
            log.info('AT updateAppStateFromConfig. Current project present. Reflecting new state', currentProjectNewState);
            appActions.reflectCurrentProjectState(appState, currentProjectNewState);
        }
    }
}
