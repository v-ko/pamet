import "./App.css";
import { observer } from "mobx-react-lite";
import { PageView } from "../../components/page/PageView";
import { PageViewState } from "../../components/page/PageViewState";
import { computed, makeObservable, observable } from "mobx";
import { pamet } from "../../facade";
import { getLogger } from "../../fusion/logging";
import { appActions } from "../../actions/app";
import { useEffect } from "react";

let log = getLogger("App");

// Define the app state with mobx and typescript
export class WebAppState {
  // Define the state
  currentPageId: string | null = null;
  errorMessage: string | null = null;
  currentUrlPath: string | null = null;
  loading: boolean = true

  constructor() {
    makeObservable(this, {
      currentPageId: observable,
      errorMessage: observable,
      currentUrlPath: observable,
      loading: observable,
      currentPageViewState: computed
    });
  }

  get currentPageViewState(): PageViewState | null {
    if (!this.currentPageId) {
      return null;
    }
    let page = pamet.page(this.currentPageId);
    if (!page) {
      return null;
    }
    let pageViewState = new PageViewState(page);
    return pageViewState
  }
}


const WebApp = observer(({ state }: { state: WebAppState }) => {

  const errorMessage = state.errorMessage;
  let pageViewState = state.currentPageViewState;

  useEffect(() => {
    pamet.loadAllEntitiesTMP(() => {
      log.info("Loaded all entities")
      appActions.setLoading(state, false);

      let urlPath = window.location.pathname;
      // If we're at the index page, load home or first
      if (urlPath === "/") {
        appActions.setPageToHomeOrFirst(state);

        // If the URL contains /p/ - load the page by id, else load the home page
      } else if (urlPath.includes("/p/")) {
        const pageId = urlPath.split("/")[2];

        // Get the page from the pages array
        const page = pamet.findOne({ id: pageId });
        if (page) {
          appActions.setCurrentPage(state, page.id);
        } else {
          appActions.setErrorMessage(state, `Page with id ${pageId} not found`);
          console.log("Page not found", pageId)
          // console.log("Pages", pages)
          appActions.setCurrentPage(state, null);
        }
      } else {
        console.log("Url not supported", urlPath)
        appActions.setCurrentPage(state, null);
      }
    });
  }, [state]);

  return (
    <div className="app">
      {/* If error message - display it */}
      {errorMessage && <div>{errorMessage}</div>}

      {/* If loading - display loading */}
      {state.loading && <div>Loading...</div>}

      {/* If page data - display the page */}
      {pageViewState && <PageView state={pageViewState} />}
    </div>
  );
});

export default WebApp;
