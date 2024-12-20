import { PageError, ProjectError, WebAppState } from "../containers/app/App";
import type { LocalStorageState } from "../containers/app/App";
import { pamet } from "../core/facade";
import { getLogger } from "fusion/logging";
import { action } from "fusion/libs/Action";
import { PageViewState } from "../components/page/PageViewState";
import type { ProjectData } from "../model/config/Project";


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
            state.pageError = PageError.NO_ERROR;
        } else {
            console.log("Page not found. FDS:", pamet.frontendDomainStore)
            log.error('Page not found in the domain store.')
            state.currentPageId = null;
            state.currentPageViewState = null;
            state.pageError = PageError.NOT_FOUND;
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
    setCurrentProject(state: WebAppState, projectData: ProjectData | null, projectError: ProjectError = ProjectError.NONE) {
        state.currentProjectId = projectData ? projectData.id : null;
        state.projectError = projectError;
    }
}

export const appActions = new AppActions();
