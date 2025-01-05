import { getLogger } from "fusion/logging";
import { appActions } from "../../actions/app";
import { projectActions } from "../../actions/project";
import { pamet } from "../../core/facade";
import { Page } from "../../model/Page";
import { WebAppState } from "../../containers/app/App";
import { PametRoute, parseUrl, toUrlPath } from "./route";

const log = getLogger('RoutingService');


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
        const url = toUrlPath(route);
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
                let firstProjectRoute = new PametRoute()
                firstProjectRoute.projectId = projects[0].id;
                this.setRoute(firstProjectRoute);
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

            if(goToPageId !== undefined) {
                let defaultPageRoute = new PametRoute();
                defaultPageRoute.projectId = projectId;
                defaultPageRoute.pageId = goToPageId;
                this.setRoute(defaultPageRoute);
            } else {
                log.error('Could not find/create a page to go to.');
            }
        }
    }

    routeFromAppState(state: WebAppState): PametRoute {
        let route = new PametRoute();
        let projectId = state.currentProjectId;
        let pageId = state.currentPageId;

        if (projectId === null && pageId !== null) {
            throw new Error('Page id set without project id. Removing page id.');
        }

        if (projectId) {
            route.projectId = projectId;
        }
        if (pageId) {
            route.pageId = pageId;
        }

        return route;
    }

    pushRoute(route: PametRoute): void {
        log.info('Pushing route', route);
        const url = toUrlPath(route);
        window.history.pushState({}, '', url);
    }

    replaceRoute(route: PametRoute): void {
        log.info('Replacing route', route);
        const url = toUrlPath(route);
        window.history.replaceState({}, '', url);
    }
}
