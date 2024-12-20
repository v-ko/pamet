import "./App.css";
import { useEffect } from "react";
import { makeObservable, observable } from "mobx";
import { observer } from "mobx-react-lite";

import { PageView } from "../../components/page/PageView";
import { PageViewState } from "../../components/page/PageViewState";

import { getLogger } from "fusion/logging";
import { DeviceData } from "web-app/src/model/config/Device";
import { UserData } from "web-app/src/model/config/User";
import { pamet } from "../../core/facade";

let log = getLogger("App");

export enum PageError {
  NO_ERROR = 0,
  NOT_FOUND = 1
}

export enum ProjectError {
  NONE = 0,
  NOT_FOUND = 1
}

export interface LocalStorageState {
  available: boolean;

}

export interface PametStorageState {
  localStorage: LocalStorageState;


}

export enum PametAppLifeCycleState {

}

export class WebAppState {
  deviceId: string | null = null;
  userId: string | null = null;

  currentProjectId: string | null = null;
  projectError: ProjectError = ProjectError.NONE;

  currentPageId: string | null = null;
  currentPageViewState: PageViewState | null = null;
  pageError: PageError = PageError.NO_ERROR;

  storageState: PametStorageState = {
    localStorage: {
      available: false
    }
  }

  constructor() {
    makeObservable(this, {
      deviceId: observable,
      userId: observable,
      currentProjectId: observable,
      currentPageViewState: observable,
      storageState: observable,
      pageError: observable,
      projectError: observable,
    });
  }

  get device(): DeviceData | null {
    if (!this.deviceId) {
      return null
    }
    let deviceData = pamet.config.deviceData
    if (!deviceData) {
      throw new Error("DeviceData missing.")
    }
    return deviceData
  }
  get user(): UserData | null {
    if (!this.userId) {
      return null
    }
    let userData = pamet.config.userData
    if (!userData) {
      throw new Error("UserData missing.")
    }
    return userData
  }
  get currentProject() {
    if (!this.currentProjectId) {
      return null
    }
    let projectData = pamet.project(this.currentProjectId)
    if (!projectData) {
      throw new Error("ProjectData missing.")
    }
    return projectData
  }
}


const WebApp = observer(({ state }: { state: WebAppState }) => {
  let errorMessages: string[] = []


  // Change the title when the current page changes
  useEffect(() => {
    if (state.currentPageViewState) {
      document.title = state.currentPageViewState.page.name;
    } else {
      document.title = "Pamet";
    }
  }, [state.currentPageViewState]);

  // Check for resurce availability, and prep error messages if needed
  if (!state.device) {
    errorMessages.push('DeviceData missing. This is a pretty critical error.')
  }
  let localStorageAvailable = state.storageState.localStorage.available;
  let shouldDisplayPage = true
  if (!localStorageAvailable) {
    errorMessages.push("Local storage not available.")
  }
  if (!localStorageAvailable || state.currentPageViewState === null) {
    shouldDisplayPage = false
  }

  if (state.projectError === ProjectError.NOT_FOUND) {
    errorMessages.push("Project not found")
    shouldDisplayPage = false
  } else {
    if (state.pageError === PageError.NOT_FOUND) {
      errorMessages.push("Page not found")
      shouldDisplayPage = false
    }

    if (state.currentPageViewState === null && state.pageError === PageError.NO_ERROR) {
      errorMessages.push("Page not set")
    }

    if (errorMessages.length > 0) {
      console.log('App error messages', errorMessages, state)
    }
  }

  return (
    <div className="app">
      {/* Display messages */}
      {errorMessages.map((message, index) => (
        <div key={index}>{message}</div>
      ))}

      {/* If page data - display the page */}
      {shouldDisplayPage && <PageView state={state.currentPageViewState!} />}
    </div>
  );
});

export default WebApp;
