import { WebAppState } from "../containers/app/App";
import { pamet } from "../facade";
import { getLogger } from "../fusion/logging";
import { action } from "../fusion/libs/action";

let HOME_PAGE_ID = "home";

let log = getLogger("WebAppActions");

export class WebAppActions {
    // constructor() {
    //     makeObservable(this);
    // }

    // @action
    // setCurrentUrlPath(state: WebAppState, urlPath: string) {
    //     state.currentUrlPath = urlPath;
    // }

    @action
    static setLoading(state: WebAppState, loading: boolean) {
        state.loading = loading;
        // if (loading) {
        //     state.errorMessage = 'Loading...';
        // } else {
        //     state.errorMessage = '';
        // }
    }

    @action
    static setCurrentPage(state: WebAppState, pageId: string | null) {
        console.log(`Changing current page to ${pageId}`)
        if (pageId === null) {
            state.currentPageId = null
            return
        }
        let page = pamet.page(pageId)
        if (!page) {
            throw new Error(`Page ${pageId} does not exist`)
        }
        state.currentPageId = page.id
    }

    @action
    static setErrorMessage(state: WebAppState, message: string) {
        state.errorMessage = message;
    }

    @action
    static setPageToHomeOrFirst(state: WebAppState) {
        let page = pamet.findOne({id: HOME_PAGE_ID});
        if (!page) {
            log.warning("No home page found");
            page = pamet.pages().next().value;
            if(page === undefined) {
                throw new Error("No pages found");
            }
        }
        WebAppActions.setCurrentPage(state, page.id);
    }
}
