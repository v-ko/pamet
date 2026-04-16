import { getLogger } from "fusion/logging";
import { pamet } from "@/core/facade";
import { PametProjectData, ProjectData } from "@/model/Project";
import { appActions } from "@/actions/app";
import { pageActions } from "@/actions/page";
import { PametRoute } from "@/services/routing/route";
import { ProjectError, WebAppState } from "@/containers/app/WebAppState";
import { Point2D } from "fusion/primitives/Point2D";
import { projectActions } from "@/actions/project";
import { Page } from "@/model/Page";
import { createId, currentTime, timestamp } from "fusion/util/base";

import { LOCAL_USER_ID } from "@/core/constants";

const log = getLogger('AppProcedures');


// --- Pure helpers (no side effects) ---

/** Resolve the best page to show. Returns pageId or null. Never creates anything. */
export function resolveStartupPageId(projectData: PametProjectData): string | null {
    const homePageId = projectData.home_page_id;
    if (homePageId) {
        const page = pamet.findOne({ id: homePageId });
        if (page) return homePageId;
    }
    const firstPage = pamet.findOne({ type: Page });
    return firstPage ? firstPage.id : null;
}


// --- Project attach/detach ---

let projectSwitchInFlight: Promise<void> | null = null;

export function switchProject(projectId: string | null): Promise<void> {
    if (projectSwitchInFlight) {
        log.error('Project switch already in progress');
        return projectSwitchInFlight;
    }

    const doSwitch = async () => {
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
        } finally {
            appActions.updateSystemDialogState(appState, null);
        }
        log.info('Project switch finished. App state:', appState);
    };

    projectSwitchInFlight = doSwitch().finally(() => { projectSwitchInFlight = null; });
    return projectSwitchInFlight;
}


// --- Route application ---

/** Apply a route to app state: switch project if needed, set page, update viewport. */
export async function applyRoute(route: PametRoute) {
    const appState = pamet.appViewState;

    // Project switch if needed (async)
    const targetProjectId = route.projectId ?? null;
    if (appState.currentProjectId !== targetProjectId) {
        await switchProject(targetProjectId);
    }

    // Page — use route's pageId, or resolve from project data
    const pageId = route.pageId
        ?? (appState.currentProjectState ? resolveStartupPageId(appState.currentProjectState) : null);
    if (pageId !== appState.currentPageId) {
        appActions.setCurrentPage(appState, pageId);
    }

    // Viewport
    if (appState.currentPageViewState && route.viewportCenter && route.viewportEyeHeight) {
        const [x, y] = route.viewportCenter;
        pageActions.updateViewport(
            appState.currentPageViewState,
            new Point2D([x, y]),
            route.viewportEyeHeight,
        );
    }
}


// --- Navigation procedures ---

/** Navigate to a project, resolving the best page. No auto-creation. */
export async function navigateToProject(projectId: string): Promise<void> {
    const appState = pamet.appViewState;

    if (appState.currentProjectId !== projectId) {
        await switchProject(projectId);
    }

    if (!appState.currentProjectState) return;

    const pageId = resolveStartupPageId(appState.currentProjectState);
    const route = new PametRoute({
        userId: appState.userId,
        projectId,
        pageId: pageId ?? undefined,
    });
    await pamet.navigateTo(route);
}

/**
 * Startup procedure (both modes).
 * Ensures a project and page exist (creating defaults if needed), then navigates.
 */
export async function ensureProjectAndNavigate(): Promise<void> {
    const route = pamet.router.currentRoute();
    const appState = pamet.appViewState;

    // 1. Resolve project
    let projectId = route.projectId;

    // Validate that the route's project is tracked, fall through if not
    if (projectId && !appState.trackedProject(projectId)) {
        projectId = undefined;
    }

    if (!projectId) {
        const projects = pamet.trackedProjects();
        if (projects.length === 0) {
            log.info('No projects found. Creating a default one');
            const newProject = await createDefaultProject();
            projectId = newProject.id;
        } else {
            projectId = projects[0].id;
        }
    }

    // 2. Attach project
    await switchProject(projectId);
    if (!appState.currentProjectState) return;

    // 3. Resolve page (from route or default), create if needed
    let pageId = route.pageId ?? resolveStartupPageId(appState.currentProjectState);
    if (!pageId) {
        log.info('No pages found in project. Creating a home page');
        let page = projectActions.createNewPageWithHelpNote();
        projectActions.setHomePage(appState, page.id);
        pageId = resolveStartupPageId(appState.currentProjectState);
    }

    // 4. Build route and navigate
    const finalRoute = new PametRoute({
        userId: appState.userId,
        projectId,
        pageId: pageId ?? undefined,
    });
    // Preserve viewport from original route if targeting the same page
    if (route.pageId === pageId && route.viewportCenter) {
        finalRoute.viewportCenter = route.viewportCenter;
        finalRoute.viewportEyeHeight = route.viewportEyeHeight;
    }
    await pamet.navigateTo(finalRoute);
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
        await switchProject(null);
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
        pamet.removeRecentProject(project.id);

        // Erase local caches; each adapter erases only what it owns
        await pamet.storageService.removeProject(project.id, pamet.projectStorageConfig(project.id));

        // If the current project is null (i.e. we've deleted the current project)
        // use the auto-assist to switch to the first project in the list
        // and create home page if needed, etc.
        if (deletingCurrentProject) {
            await ensureProjectAndNavigate();
        }

        log.info("Project removal procedure completed");
    } finally {
        appActions.updateSystemDialogState(pamet.appViewState, null);
    }
}


export async function updateAppStateFromConfig(appState: WebAppState) {
    // Device
    let deviceId = pamet.getDeviceId() ?? null;

    // User - For now UserData has no id/name, so we use LOCAL_USER_ID
    // Later when cloud auth is implemented, this will set the actual user ID
    let user = pamet.getUserData();
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
        pamet.getTrackedProjectsFromConfig(),
        pamet.getRecentProjects(),
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

export async function createProject(newProject: ProjectData): Promise<void> {
    log.info('Creating project', newProject.id);
    const projectUri = await pamet.storageService.createProject(
        newProject.id,
        pamet.projectStorageConfig(newProject.id),
    );
    pamet.saveProjectProperties(newProject);
    pamet.upsertTrackedProject({
        id: newProject.id,
        title: newProject.title,
        uri: projectUri,
    });
    pamet.setMostRecentProject({
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
