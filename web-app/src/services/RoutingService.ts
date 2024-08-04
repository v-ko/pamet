import { getLogger } from "fusion/logging";
import { appActions } from "../actions/app";
import { projectActions } from "../actions/project";
import { pamet } from "../core/facade";
import { Page } from "../model/Page";

const log = getLogger('RoutingService');


export interface PametRoute {
    projectId?: string;
    pageId?: string;
    viewportCenter?: [number, number];
    viewportEyeHeight?: number;
    focusedNoteId?: string;
}

function parseUrl(url: string): PametRoute {
    const url_ = new URL(url);
    const path = url_.pathname;
    const search = url_.search;
    const hash = url_.hash;

    let route: PametRoute = {
        projectId: undefined,
        pageId: undefined,
        viewportCenter: undefined,
        viewportEyeHeight: undefined,
        focusedNoteId: undefined,
    };

    // Parse the path
    const pathParts = path.split('/');
    if (pathParts.length >= 3 && pathParts[1] === 'project' && pathParts[2].length === 8) {
        route.projectId = pathParts[2];
    }
    if (pathParts.length >= 5 && pathParts[3] === 'page' && pathParts[4].length === 8) {
        route.pageId = pathParts[4];
    }

    // Parse the search
    const searchParams = new URLSearchParams(search);
    const eye_at = searchParams.get('eye_at');
    if (eye_at) {
        const [eyeHeight, x, y] = eye_at.split('/').map(parseFloat);
        if (!isNaN(eyeHeight) && !isNaN(x) && !isNaN(y)) {
            route.viewportEyeHeight = eyeHeight;
            route.viewportCenter = [x, y];
        }
    }

    // Parse the hash
    if (hash.startsWith('#note=')) {
        route.focusedNoteId = decodeURIComponent(hash.substring(6));
    }

    return route;
}

function toUrl(route: PametRoute): string {
    if (!route.projectId) {
        return '/';
    }

    let path = `/project/${encodeURIComponent(route.projectId)}`;

    if (route.pageId && route.pageId.length === 8) {
        path += `/page/${encodeURIComponent(route.pageId)}`;
    }

    let search = '';
    if (route.viewportEyeHeight && route.viewportCenter) {
        search = `?eye_at=${encodeURIComponent(route.viewportEyeHeight.toString())}/${encodeURIComponent(route.viewportCenter[0].toString())}/${encodeURIComponent(route.viewportCenter[1].toString())}`;
    }

    let hash = '';
    if (route.focusedNoteId) {
        hash = `#note=${encodeURIComponent(route.focusedNoteId)}`;
    }

    return path + search + hash;
}

export class RoutingService {
    private routingListener: (() => void) | null = null;

    get autoHandleRouteChange(): boolean {
        return !!this.routingListener
    }

    currentRoute(): PametRoute {
        return parseUrl(window.location.href);
    }
    setRoute(route: PametRoute): void {
        log.info('Setting route', route)
        const url = toUrl(route);
        window.history.pushState({}, '', url);

        if (this.autoHandleRouteChange) {
            setTimeout(() => {
                this.reachRouteOrAutoassist(route);
            });
        }
    }

    handleRouteChange(enable: boolean): void {
        if (enable) {
            if (this.routingListener) {
                throw Error('Route change handling already enabled');
            }
            this.routingListener = () => {
                const route = this.currentRoute();
                log.info('Route changed, calling handler');
                this.reachRouteOrAutoassist(route);
            };
            window.addEventListener('popstate', this.routingListener);
        } else if (!enable) {
            if (this.routingListener) {
                window.removeEventListener('popstate', this.routingListener);
                this.routingListener = null;
            } else {
                throw Error('Route change handling already disabled');
            }
        }
    }

    async reachRouteOrAutoassist(route: PametRoute): Promise<void> {
        log.info('reachRouteOrAutoassist for route', route);

        // "Reaches" the route by executing the necessary app configuration

        let projectId: string

        // If there's a projectId - switch to the project
        if (route.projectId === undefined) {
            // go to default project
            let projects = pamet.projects();
            if (projects.length === 0) {
                throw Error('No projects found');
            } else {
                log.info('Switching to the first project');
                // TEST IF THIS NOTIFIES back to the handler
                this.setRoute({ projectId: projects[0].id })
                return;
            }
        }

        projectId = route.projectId;
        // Get project data from config
        let userData = pamet.config.userData;
        if (!userData) {
            throw Error('User data not loaded');
        }

        await pamet.setCurrentProject(projectId); // view state updated here

        // if there's a page id
        let pageId = route.pageId;
        if (pageId !== undefined) {
            // // TMP - if missing redirect to project
            // let page = pamet.findOne({ id: pageId });
            // if (!page) {
            //     log.error('Page not found in the repo for id', pageId);
            //     log.info('Removing page id from the route')
            //     log.info("REMOVE THIS LATER")
            //     this.setRoute({ projectId: projectId });
            //     return;
            // }
            appActions.setCurrentPage(pamet.appViewState, pageId);
        } else {  // If there's no page id
            // Goto first/default page
            let goToPageId: string | undefined = undefined;

            // Check for default page in the project
            let projectData = pamet.project(projectId);
            if (projectData.defaultPageId) {
                // Check that the page is present
                let page = pamet.findOne({ id: projectData.defaultPageId });
                if (!page) { // If the default page is set, but missing
                    log.error('Default page not found in the repo for id', projectData.defaultPageId);
                    log.info('Removing default page id from the project')
                    // Set defaultPageId to null in the project
                    projectData.defaultPageId = undefined;
                    pamet.updateProject(projectData);
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
                    projectActions.createDefaultPage(pamet.appViewState);
                    let newPage = pamet.findOne({ type: Page });
                    if (!newPage) {
                        throw Error('Default page not created');
                    }
                    log.info('Switching to the newly created default page', newPage);
                    goToPageId = newPage.id;
                }
            }

            if(goToPageId !== undefined) {
                this.setRoute({ projectId: projectId, pageId: goToPageId });
            } else {
                log.error('Could not find/create a page to go to.');
            }
        }
    }
}
