import { getLogger } from "fusion/logging";
import { pamet } from "@/core/facade";
import { ProjectData } from "@/model/config/Project";
import { appActions } from "@/actions/app";
import { PametRoute } from "@/services/routing/route";
import { ProjectError, WebAppState } from "@/containers/app/WebAppState";
import { projectActions } from "@/actions/project";
import { Page } from "@/model/Page";
import { createId, currentTime, timestamp } from "fusion/util/base";
import { DesktopImporter } from "@/storage/DesktopImporter";
import { pageActions } from "@/actions/page";
import { Point2D } from "fusion/primitives/Point2D";

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
    log.info('Switching to project', projectId);

    const appState = pamet.appViewState;
    appActions.updateSystemDialogState(appState, {title: 'Switching project...'});
    // await new Promise(resolve => setTimeout(resolve, 50)); // Simulate delay

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
            await pamet.detachFromProject(currentProjectId!);
        }

        if (shouldAttachNew) {
            await pamet.attachProjectAsCurrent(projectData!.id);
        }

        // Reflect the new project state in the app state
        // If we've attached a new project we update the view state
        // If the project is the same - again we update the view state for good measure
        if (shouldAttachNew || (idsMatch && projectData)) {
            appActions.reflectCurrentProjectState(appState, projectData!);
            projectActions.goToDefaultPage(pamet.appViewState);
            return;
            // If the request is to detach the FDS - reflect that
        } else if (projectId === null) {
            appActions.reflectCurrentProjectState(appState, null);

            // If a request is made to load a project but it's not found, set error
        } else if (projectId !== null && !projectFound) {
            appActions.reflectCurrentProjectState(appState, null, ProjectError.NotFound);
        }

        // The state is updated - URL will sync via router reaction
    } finally {
        projectSwithLock = false;
        appActions.updateSystemDialogState(appState, null);
    }
    log.info('Project switch finished. App state:', pamet.appViewState);
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

    // Ask here, so that there's no chance another tab creates the default
    // project first, creating a conflict
    if (pamet.projects().length === 1) {
        alert('You\'re deleting the last project. A new one will be created.')
    }

    // If the project to be deleted is the currently open one
    // we detach
    if (pamet.appViewState.currentProjectId === project.id) {
        log.info("Detaching FDS");
        await switchToProject(null);
    }

    // Do the requested delete from the local config and storage backend
    log.info("Removing project from config and indexeddb", project);
    appActions.updateSystemDialogState(pamet.appViewState, {
        title: 'Deleting project...',
        taskProgress: -1,
    });

    // Remove from config which will signal the other tabs to unload the project
    pamet.config.removeProject(project.id);

    await pamet.storageService.deleteProject(
        project.id,
        pamet.projectStorageConfig(project.id)
    )
    // auto-creation is handled in auto-assist i think
    // // If there's no projects left, create a default one
    // if (pamet.projects().length === 0) {
    //     log.info("No projects left - creating a default one");
    //     appActions.updateSystemDialogState(pamet.appViewState, {
    //         title: 'Creating default project...',
    //         taskProgress: 100,
    //     });
    //     let newProject = await createDefaultProject();
    //     await switchToProject(newProject.id);
    // }

    // If the current project is null (i.e. we've deleted the current project)
    // Use the auto-assist to switch to the first project in the list
    // and create default page if needed, etc
    if (pamet.appViewState.currentProjectId === null) {
        await updateAppFromRouteOrAutoassist(new PametRoute());
    }

    log.info("Project deletion procedure completed");
}


export async function updateAppFromRoute(route: PametRoute): Promise<void> {
    // Reflects the route in the app state without any URL mutations
    log.info('updateAppFromRoute for route', route);

    const appState = pamet.appViewState;

    // 1) Project
    const targetProjectId = route.projectId ?? null;
    if (appState.currentProjectId !== targetProjectId) {
        await switchToProject(targetProjectId);
    }

    // 2) Page
    const targetPageId = route.pageId ?? null;
    if (appState.currentPageId !== targetPageId) {
        if (targetPageId) {
            appActions.setCurrentPage(appState, targetPageId);
        } else {
            // Leave current page as-is when clearing pageId via pure reflect
            // If needed, higher-level auto-assist decides defaults
        }
    }

    // 3) Viewport (view_at) for current page, if provided
    if (appState.currentPageViewState && route.viewportCenter && route.viewportEyeHeight) {
        const [x, y] = route.viewportCenter;
        pageActions.updateViewport(appState.currentPageViewState, new Point2D([x, y]), route.viewportEyeHeight);
    }
}

export async function updateAppFromRouteOrAutoassist(route: PametRoute): Promise<void> {
    // "Reaches" the route by executing the necessary app configuration
    log.info('updateAppFromRouteOrAutoassist for route', route);

    // Get project data from config
    let userId = pamet.appViewState.userId;
    if (userId === null) {
        log.error('User ID is not set. Cannot update app from route.');
        return;
    }

    // If no project id - go to default project (or create one)
    let projectId = route.projectId;
    if (projectId === undefined) {
        // go to default project
        let projects = pamet.projects();
        if (projects.length === 0) {
            log.info('No projects found. Creating a default one');
            let newProject = await createDefaultProject();
            await switchToProject(newProject.id);
            await updateAppFromRouteOrAutoassist(new PametRoute());
            return;
        } else {
            log.info('Switching to the first project');
            let firstProjectRoute = new PametRoute({
                userId: userId,
                projectId: projects[0].id,
            })
            await switchToProject(projects[0].id);
            return;
        }
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
        // Apply viewport (eye_at) if provided
        if (pamet.appViewState.currentPageViewState && route.viewportCenter && route.viewportEyeHeight) {
            const [x, y] = route.viewportCenter;
            pageActions.updateViewport(pamet.appViewState.currentPageViewState, new Point2D([x, y]), route.viewportEyeHeight);
        }
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
            appActions.setCurrentPage(pamet.appViewState, goToPageId);
            // Apply viewport (eye_at) if provided
            if (pamet.appViewState.currentPageViewState && route.viewportCenter && route.viewportEyeHeight) {
                const [x, y] = route.viewportCenter;
                pageActions.updateViewport(pamet.appViewState.currentPageViewState, new Point2D([x, y]), route.viewportEyeHeight);
            }
        } else {
            log.error('Could not find/create a page to go to.');
        }
    }
}

export async function updateAppStateFromConfig(appState: WebAppState) {
    // Device
    let device = pamet.config.getDeviceData();
    if (device === undefined) {
        appState.deviceId = null;
    } else {
        appState.deviceId = device.id;
    }

    // User
    let user = pamet.config.getUserData();
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

export async function importDesktopDataForTesting() {
    log.info('Starting import of desktop data for testing...');
    const appState = pamet.appViewState;

    appActions.updateSystemDialogState(appState, {title: 'Starting import...'});
    await new Promise(resolve => setTimeout(resolve, 500)); // Simulate delay

    try {
        // 1. Create a new project for the imported data
        appActions.updateSystemDialogState(appState, {title: 'Creating new project...'});

        const newProject: ProjectData = {
            id: `desktop-import-${createId()}`,
            title: 'Desktop Import',
            description: 'Imported from desktop server',
            owner: pamet.config.getUserData()!.id,
            created: timestamp(currentTime()),
        };
        await createProject(newProject);

        // 2. Switch to the new project
        appActions.updateSystemDialogState(appState, {title: 'Switching to new project...'});
        await switchToProject(newProject.id);

        // 3. Fetch data from desktop server and import it
        const desktopImporter = new DesktopImporter("http://localhost", 11352);
        await desktopImporter.importAllInProject((progress: number, message: string) => {
            appActions.updateSystemDialogState(appState, {title: message, taskProgress: progress});
        });

        log.info(`Imported entities into project ${newProject.id}`);

    } catch (e) {
        log.error('Failed to import desktop data', e);
        alert('Failed to import desktop data. See console for details.');
    } finally {
        // 6. Close the dialog
        appActions.updateSystemDialogState(appState, null);
    }
    projectActions.goToDefaultPage(appState);
}

export async function createProject(newProject: ProjectData): Promise<void> {
    log.info('Creating project', newProject.id);
    await pamet.storageService.createProject(newProject.id, pamet.projectStorageConfig(newProject.id));
    pamet.config.addProject(newProject);
    log.info('Project created and added to config', newProject.id);
}

export async function createDefaultProject(): Promise<ProjectData> {
    const newProject: ProjectData = {
        id: 'notebook',
        title: 'Notebook',
        description: 'Default project',
        owner: pamet.config.getUserData()!.id,
        created: timestamp(currentTime()),
    };
    await createProject(newProject);
    return newProject;
}

export async function restartServiceWorker(): Promise<void> {
    log.info('Restarting service worker...');
    await pamet.storageService.unregisterServiceWorker();
    log.info('Service worker restarted. Reloading page...');
    window.location.reload();
}
