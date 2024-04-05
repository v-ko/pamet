import { WebAppState } from "../containers/app/App";
import { pamet } from "../facade";
import { getLogger } from "../fusion/logging";
import { action } from "../fusion/libs/Action";
import { PageViewState } from "../components/page/PageViewState";

let HOME_PAGE_ID = "home";

let log = getLogger("WebAppActions");

class AppActions {
    @action
    setLoading(state: WebAppState, loading: boolean) {
        state.loading = loading;
    }

    @action
    setCurrentPage(state: WebAppState, pageId: string | null) {
        console.log(`Changing current page to ${pageId}`)
        // if (pageId === null) {
        //     state.currentPageId = null
        //     return
        // }
        // let page = pamet.page(pageId)
        // if (!page) {
        //     throw new Error(`Page ${pageId} does not exist`)
        // }
        // state.currentPageId = page.id
        if (!pageId) {
            return null;
        }
        let page = pamet.page(pageId);

        if (page) {
            state.currentPageViewState = new PageViewState(page);
        } else {
            state.currentPageViewState = null;
        }

    }

    @action
    setErrorMessage(state: WebAppState, message: string) {
        state.errorMessage = message;
    }

    @action
    setPageToHomeOrFirst(state: WebAppState) {
        let page = pamet.findOne({ id: HOME_PAGE_ID });
        if (!page) {
            log.info("No home page found");
            page = pamet.pages().next().value;
            if (page === undefined) {
                throw new Error("No pages found");
            }
        }
        appActions.setCurrentPage(state, page.id);
    }
}

export const appActions = new AppActions();
