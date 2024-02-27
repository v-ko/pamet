import "./App.css";
import { observer } from "mobx-react-lite";
import { MapPageComponent } from "../../components/canvas/Page";
import { PageViewState } from "../../components/canvas/PageViewState";
import { computed, makeObservable, observable } from "mobx";
import { pamet } from "../../facade";
import { getLogger } from "../../fusion/logging";

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
    if(!this.currentPageId) {
      return null;
    }
    let page = pamet.page(this.currentPageId);
    if(!page) {
      return null;
    }
    let pageViewState = new PageViewState(page);
    return pageViewState
  }
}


const WebApp = observer(({ state }: { state: WebAppState}) => {

  const errorMessage = state.errorMessage;
  let pageViewState = state.currentPageViewState;

  // log.info('Page view state: ', pageViewState);

  return (
    <div className="app">
      {/* If error message - display it */}
      {errorMessage && <div>{errorMessage}</div>}

      {/* If loading - display loading */}
      {state.loading && <div>Loading...</div>}

      {/* If page data - display the page */}
      {pageViewState && <MapPageComponent state={pageViewState} />}
    </div>
  );
});

export default WebApp;
