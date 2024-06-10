import "./App.css";
import { useEffect } from "react";
import { makeObservable, observable } from "mobx";
import { observer } from "mobx-react-lite";

import { PageView } from "../../components/page/PageView";
import { PageViewState } from "../../components/page/PageViewState";

import { getLogger } from "pyfusion/logging";
import { UserData } from "web-app/src/model/User";
import { DeviceData } from "web-app/src/model/Device";

let log = getLogger("App");

export enum PageError {
  NONE = 0,
  NOT_FOUND = 1
}

export class WebAppState {
  device: DeviceData | null = null;
  user: UserData | null = null;

  currentPageViewState: PageViewState | null = null;
  pageError: PageError = PageError.NONE;
  currentUrlPath: string | null = null;
  loading: boolean = true

  constructor() {
    makeObservable(this, {
      pageError: observable,
      currentUrlPath: observable,
      loading: observable,
      currentPageViewState: observable
    });
  }
}


const WebApp = observer(({ state }: { state: WebAppState }) => {
  let errorMessage: string = '';

  if (state.pageError === PageError.NOT_FOUND) {
    errorMessage = "Page not found";
  }


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
