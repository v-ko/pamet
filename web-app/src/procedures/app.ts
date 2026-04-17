import { getLogger } from "fusion/logging";
import { pamet } from "@/core/facade";
import { ProjectData } from "@/model/Project";
import { appActions } from "@/actions/app";
import { pageActions } from "@/actions/page";
import { PametRoute } from "@/services/routing/route";
import { ProjectError, AppViewState } from "@/views/AppViewState";
import { Point2D } from "fusion/primitives/Point2D";
import { projectActions } from "@/actions/project";
import { Page } from "@/model/Page";
import { currentTime, timestamp } from "fusion/util/base";

const log = getLogger('AppProcedures');


// --- Project attach/detach ---

let projectSwitchInFlight: Promise<void> | null = null;

export function switchProject(projectId: string | null): Promise<void> {
    if (projectSwitchInFlight) {
        log.error('Project switch already in progress');
        return projectSwitchInFlight;
    }

    const doSwitch = async () => {
        log.info('Switching to project', projectId);
        const appViewState = pamet.appViewState;
        appActions.updateSystemDialogState(appViewState, {title: 'Switching project...'});

        try {
            const currentProjectId = appViewState.currentProjectId;

            // Case 1: Detach (no target project)
            if (projectId === null) {
                if (currentProjectId) {
                    await pamet.detachFromProject(currentProjectId);
                }
                appActions.reflectCurrentProjectState(appViewState, null);
                return;
            }

            // Case 2: Same project — just ensure properties are loaded
            if (projectId === currentProjectId) {
                const projectData = appViewState.currentProjectState
                    ?? pamet.loadProjectProperties(projectId);
                if (projectData) {
                    appActions.reflectCurrentProjectState(appViewState, projectData);
                }
                return;
            }

            // Case 3: Different project
            if (currentProjectId) {
                await pamet.detachFromProject(currentProjectId);
            }

            if (!appViewState.trackedProject(projectId)) {
                appActions.reflectCurrentProjectState(appViewState, null, ProjectError.NotFound);
                return;
            }

            await pamet.attachProjectAsCurrent(projectId);
            const projectData = pamet.loadProjectProperties(projectId);
            appActions.reflectCurrentProjectState(appViewState, projectData ?? null);
        } finally {
            appActions.updateSystemDialogState(appViewState, null);
        }
        log.info('Project switch finished. App view state:', appViewState);
    };

    projectSwitchInFlight = doSwitch().finally(() => { projectSwitchInFlight = null; });
    return projectSwitchInFlight;
}


// --- Route application ---

/** Apply a route to app view state: switch project if needed, set page, update viewport. */
export async function applyRoute(route: PametRoute) {
    const appViewState = pamet.appViewState;

    // Project switch if needed (async)
    const targetProjectId = route.projectId ?? null;
    if (appViewState.currentProjectId !== targetProjectId) {
        await switchProject(targetProjectId);
    }

    // Page — use route's pageId, or fall back to home page
    const pageId = route.pageId
        ?? (appViewState.currentProjectState?.home_page_id ?? null);
    if (pageId !== appViewState.currentPageId) {
        appActions.setCurrentPage(appViewState, pageId);
    }

    // Viewport
    if (appViewState.currentPageViewState && route.viewportCenter && route.viewportEyeHeight) {
        const [x, y] = route.viewportCenter;
        pageActions.updateViewport(
            appViewState.currentPageViewState,
            new Point2D([x, y]),
            route.viewportEyeHeight,
        );
    }
}


// --- Navigation procedures ---

/** Delete a page, create home if last, then navigate. */
export async function deletePageAndNavigate(appViewState: AppViewState, page: Page): Promise<void> {
    projectActions.deletePageAndUpdateReferences(page);
    appActions.closeAppDialog(appViewState);

    let pageId = appViewState.currentProjectState?.home_page_id ?? null;
    if (!pageId && appViewState.currentProjectState) {
        let newPage = projectActions.createNewPageWithHelpNote();
        projectActions.setHomePage(appViewState, newPage.id);
        pageId = newPage.id;
    }
    await pamet.navigateTo(new PametRoute({
        userId: appViewState.userId,
        projectId: appViewState.currentProjectId ?? undefined,
        pageId: pageId ?? undefined,
    }));
}

/** Create a new page (with links) and navigate to it. */
export async function createPageAndNavigate(appViewState: AppViewState, name: string): Promise<void> {
    let page = projectActions.createNewPage(appViewState, name);
    await pamet.navigateTo(new PametRoute({
        userId: appViewState.userId,
        projectId: appViewState.currentProjectId ?? undefined,
        pageId: page.id,
    }));
}

/** Navigate to a project, resolving the best page. No auto-creation. */
export async function navigateToProject(projectId: string): Promise<void> {
    const appViewState = pamet.appViewState;

    if (appViewState.currentProjectId !== projectId) {
        await switchProject(projectId);
    }

    if (!appViewState.currentProjectState) return;

    const pageId = appViewState.currentProjectState.home_page_id;
    const route = new PametRoute({
        userId: appViewState.userId,
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
    const appViewState = pamet.appViewState;

    // 1. Resolve project
    let projectId = route.projectId;

    // Validate that the route's project is tracked, fall through if not
    if (projectId && !appViewState.trackedProject(projectId)) {
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
    if (!appViewState.currentProjectState) return;

    // 3. Resolve page (from route or home page), create if needed
    let pageId = route.pageId ?? appViewState.currentProjectState.home_page_id;
    if (!pageId) {
        log.info('No home page set. Creating a home page');
        let page = projectActions.createNewPageWithHelpNote();
        projectActions.setHomePage(appViewState, page.id);
        pageId = page.id;
    }

    // 4. Build route and navigate
    const finalRoute = new PametRoute({
        userId: appViewState.userId,
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
        if (pamet.recentProjects().some(p => p.id === project.id)) {
            pamet.removeRecentProject(project.id);
        }

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
