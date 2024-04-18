import "./App.css";
import { observer } from "mobx-react-lite";
import { PageView } from "../../components/page/PageView";
import { PageViewState } from "../../components/page/PageViewState";
import { makeObservable, observable } from "mobx";
import { getLogger } from "pyfusion/logging";
import { useEffect } from "react";

let log = getLogger("App");

// Define the app state with mobx and typescript
export class WebAppState {
  // Define the state
  // currentPageId: string | null = null;
  currentPageViewState: PageViewState | null = null;
  errorMessage: string | null = null;
  currentUrlPath: string | null = null;
  loading: boolean = true

  constructor() {
    makeObservable(this, {
      // currentPageId: observable,
      errorMessage: observable,
      currentUrlPath: observable,
      loading: observable,
      currentPageViewState: observable
    });
  }
}


const WebApp = observer(({ state }: { state: WebAppState }) => {
  // const [entityLoadCalled, setEntityLoadCalled] = useState(false);
  const errorMessage = state.errorMessage;


  // Change the title when the current page changes
  useEffect(() => {
    if (state.currentPageViewState) {
      document.title = state.currentPageViewState.page.name;
    } else {
      document.title = "Pamet";
    }
  }, [state.currentPageViewState]);

  return (
    <div className="app">
      {/* If error message - display it */}
      {errorMessage && <div>{errorMessage}</div>}

      {/* If loading - display loading */}
      {state.loading && <div>Loading...</div>}

      {/* If page data - display the page */}
      {state.currentPageViewState && <PageView state={state.currentPageViewState} />}
    </div>
  );
});

export default WebApp;
