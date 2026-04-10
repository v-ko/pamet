import { getLogger } from "fusion/logging";
import { pamet } from "@/core/facade";
import { PametProjectData, ProjectData } from "@/model/Project";
import { appActions } from "@/actions/app";
import { PametRoute } from "@/services/routing/route";
import { ProjectError, WebAppState } from "@/containers/app/WebAppState";
import { projectActions } from "@/actions/project";
import { Page } from "@/model/Page";
import { createId, currentTime, timestamp } from "fusion/util/base";
import { DesktopImporter } from "@/storage/DesktopImporter";

import { pageActions } from "@/actions/page";
import { Point2D } from "fusion/primitives/Point2D";
import { LOCAL_USER_ID } from "@/core/constants";

const log = getLogger('AppProcedures');


let projectSwitchInFlight: Promise<void> | null = null;

export async function doSwitchToProject(projectId: string | null): Promise<void> {
    log.info('Switching to project', projectId);
    const appState = pamet.appViewState;
    appActions.updateSystemDialogState(appState, {title: 'Switching project...'});

    try {
        const currentProjectId = appState.currentProjectId;

        // Case 1: Detach (no target project)
        if (projectId === null) {
            if (currentProjectId) {
                await pamet.detachFromProject(currentProjectId);
            }
            appActions.reflectCurrentProjectState(appState, null);
            return;
        }

        // Case 2: Same project — just ensure properties are loaded
        if (projectId === currentProjectId) {
            const projectData = appState.currentProjectState
                ?? await pamet.loadProjectProperties(projectId);
            if (projectData) {
                appActions.reflectCurrentProjectState(appState, projectData);
                projectActions.goToDefaultPage(appState);
            }
            return;
        }

        // Case 3: Different project
        if (currentProjectId) {
            await pamet.detachFromProject(currentProjectId);
        }

        if (!appState.trackedProject(projectId)) {
            appActions.reflectCurrentProjectState(appState, null, ProjectError.NotFound);
            return;
        }

        await pamet.attachProjectAsCurrent(projectId);
        const projectData = await pamet.loadProjectProperties(projectId);
        appActions.reflectCurrentProjectState(appState, projectData ?? null);
        projectActions.goToDefaultPage(appState);
    } finally {
        appActions.updateSystemDialogState(appState, null);
    }
    log.info('Project switch finished. App state:', appState);
}

export async function switchToProject(projectId: string | null): Promise<void> {
    if (projectSwitchInFlight) {
        log.error('Project switch already in progress');
        return projectSwitchInFlight;
    }
    projectSwitchInFlight = doSwitchToProject(projectId);
    try {
        await projectSwitchInFlight;
        pamet.syncRouterFromAppState();
    } finally {
        projectSwitchInFlight = null;
    }
}


export async function deleteProjectAndSwitch(project: ProjectData) {
    // Remove the project from the config and storage, then
    // if removing the currently open project -
    // switch to another project (if none present - create a default one)
    log.info("Starting remove procedure for project", project);

    // Get projects, return error if the project is missing
    let projects = pamet.trackedProjects();
    if (!projects.find(p => p.id === project.id)) {
        throw new Error(`Project with ID ${project.id} not found`);
    }

    // Ask here, so that there's no chance another tab creates the default
    // project first, creating a conflict
    if (pamet.trackedProjects().length === 1) {
        alert('You\'re deleting the last project. A new one will be created.')
    }

    // If the project to be deleted is the currently open one - detach first
    // so that the FDS stops pushing commits before storage is torn down
    let deletingCurrentProject = pamet.appViewState.currentProjectId === project.id;
    if (deletingCurrentProject) {
        log.info("Detaching from current project before removal");
        await switchToProject(null);
    }

    // Do the requested removal from config and storage
    log.info("Removing project from config and storage", project);
    appActions.updateSystemDialogState(pamet.appViewState, {
        title: 'Removing project...',
        taskProgress: -1,
    });

    try {
        // Remove from config which will signal the other tabs to unload the project
        pamet.removeTrackedProject(project.id);
        pamet.appMiscProperties.removeRecentProject(project.id);

        // Erase local caches; each adapter erases only what it owns
        await pamet.storageService.removeProject(project.id, pamet.projectStorageConfig(project.id));

        // If the current project is null (i.e. we've deleted the current project)
        // use the auto-assist to switch to the first project in the list
        // and create default page if needed, etc.
        if (deletingCurrentProject) {
            await updateAppFromRouteOrAutoassist(new PametRoute());
        }

        log.info("Project removal procedure completed");
    } finally {
        appActions.updateSystemDialogState(pamet.appViewState, null);
    }
}


export async function updateAppFromRouteOrAutoassist(route?: PametRoute): Promise<void> {
    if (!route) {
        route = pamet.router.currentRoute();
    }
    log.info('updateAppFromRouteOrAutoassist for route', route.toString());
    const appState = pamet.appViewState;

    // 1.
    let projectId = route.projectId;
    if (projectId === undefined) {
        const projects = pamet.trackedProjects();
        if (projects.length === 0) {
            log.info('No projects found. Creating a default one');
            const newProject = await createDefaultProject();
            projectId = newProject.id;
        } else {
            log.info('Switching to the first project');
            projectId = projects[0].id;
        }
    }

    await switchToProject(projectId);

    const projectData = appState.currentProjectState;
    if (!projectData) {
        return; // 404 already set by switchToProject
    }

    // 2. Resolve page (from route or find/create default)
    let pageId = route.pageId ?? await resolveDefaultPageId(projectData);

    // 3. Apply page and viewport
    if (pageId !== undefined) {
        appActions.setCurrentPage(appState, pageId);
        if (appState.currentPageViewState && route.viewportCenter && route.viewportEyeHeight) {
            const [x, y] = route.viewportCenter;
            pageActions.updateViewport(appState.currentPageViewState, new Point2D([x, y]), route.viewportEyeHeight);
        }
    } else {
        log.error('Could not find/create a page to go to.');
    }

    pamet.syncRouterFromAppState();
}

async function resolveDefaultPageId(projectData: PametProjectData): Promise<string | undefined> {
    const defaultPageId = projectData.default_page_id;
    if (defaultPageId) {
        const page = pamet.findOne({ id: defaultPageId });
        if (page) {
            log.info('Switching to default page', defaultPageId);
            return defaultPageId;
        }
        log.error('Default page not found in the repo for id', defaultPageId);
        log.info('Removing default page id from the project');
        const { default_page_id: _removed, ...restProject } = projectData;
        await pamet.saveProjectProperties(restProject as PametProjectData);
    }

    const firstPage = pamet.findOne({ type: Page });
    if (firstPage) {
        log.info('Switching to the first page', firstPage.id);
        return firstPage.id;
    }

    log.info('No pages found in the project. Creating a default page');
    projectActions.createDefaultPage(pamet.appViewState);
    const newPage = pamet.findOne({ type: Page });
    if (!newPage) {
        throw Error('Default page not created');
    }
    log.info('Switching to the newly created default page', newPage);
    return newPage.id;
}

export async function updateAppStateFromConfig(appState: WebAppState) {
    // Device
    let deviceId = pamet.appMiscProperties.getDeviceId() ?? null;

    // User - For now UserData has no id/name, so we use LOCAL_USER_ID
    // Later when cloud auth is implemented, this will set the actual user ID
    let user = pamet.config.getUserData();
    let userId: string;
    if (!user) {
        userId = LOCAL_USER_ID;
    } else {
        if (!user.id){
            throw new Error('User data is missing id field');
        }
        userId = user.id!;
    }
    // TODO: When cloud auth is implemented, add: else { appState.userId = user.id; }

    appActions.updateIdentity(appState, deviceId, userId);
    appActions.updateProjectReferences(
        appState,
        pamet.config.getProjects(),
        pamet.appMiscProperties.getRecentProjects(),
    );

    // Settings - not yet implemented

    // Projects
    if (appState.currentProjectId) {
        // If the current project has been deleted, reload the page so that
        // the router goes to the default project
        const currentTrackedProject = pamet.appViewState.trackedProject(appState.currentProjectId);
        if (currentTrackedProject === undefined) {
            log.info('Project deleted in other tab.');
            alert('The project you were working on has been deleted in another tab. Reloading the page.');
            window.location.reload();
        } else {
            // Else update the current project data in the app state
            // * This should be implemented as a mobx reaction at some point to avoid
            // redundant updates
            const currentProjectNewState = await pamet.loadProjectProperties(appState.currentProjectId);
            log.info('AT updateAppStateFromConfig. Current project present. Reflecting new state', currentProjectNewState);
            appActions.reflectCurrentProjectState(appState, currentProjectNewState ?? null);
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
    const projectUri = await pamet.storageService.createProject(
        newProject.id,
        pamet.projectStorageConfig(newProject.id),
        newProject,
    );
    pamet.upsertTrackedProject({
        id: newProject.id,
        title: newProject.title,
        uri: projectUri,
    });
    pamet.appMiscProperties.setMostRecentProject({
        id: newProject.id,
        title: newProject.title,
        uri: projectUri,
    });
    log.info('Project created and added to config', newProject.id);
}

export async function createDefaultProject(): Promise<ProjectData> {
    const newProject: ProjectData = {
        id: 'notebook',
        title: 'Notebook',
        description: 'Default project',
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
