import "./App.css";
import { useEffect } from "react";
import { makeObservable, observable } from "mobx";
import { observer } from "mobx-react-lite";

import { MouseState, PageView } from "../../components/page/PageView";
import { PageViewState } from "../../components/page/PageViewState";

import { getLogger } from "fusion/logging";
import { DeviceData } from "web-app/src/model/config/Device";
import { UserData } from "web-app/src/model/config/User";
import { pamet } from "../../core/facade";
import { styled } from "styled-components";
import Panel from "../../components/Panel";

import cloudOffIconUrl from '../../resources/icons/cloud-off.svg';
import shareIconUrl from '../../resources/icons/share-2.svg';
import accountCircleIconUrl from '../../resources/icons/account-circle.svg';
import helpCircleIconUrl from '../../resources/icons/help-circle.svg';
import { commands } from "../../core/commands";
import { pageActions } from "../../actions/page";
import EditComponent from "../../components/note/EditComponent";
import { Point2D } from "../../util/Point2D";

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

  mouse: MouseState = new MouseState();

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


// Vertical line component
const VerticalSeparator = styled.div`
  width: 1px;
  height: 1em;
  background: rgba(0,0,0,0.2);
`

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
    errorMessages.push("Local storage not initialized/available.")
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

  const currentPageVS = state.currentPageViewState


  return (
    <div className="app">
      {/* a div for the app messages to be displayed in the center of the screen */}
      {/* use only inline css */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        textAlign: 'center',
        color: 'red',
        fontWeight: 'bold',
        fontSize: '1.5em',
      }}>

        {/* Display messages */}
        {errorMessages.map((message, index) => (
          <div key={index}>{message}</div>
        ))}
      </div>


      {/* If page data - display the page */}
      {shouldDisplayPage && <PageView state={state.currentPageViewState!} />}


      {/* Main panel - logo, project name, save state, help button */}
      <Panel align='top-left'>

        <div
          style={{
            fontSize: '1.1em',
            fontWeight: 400,
            cursor: 'pointer',
          }}
          onClick={() => { alert('Not implemented yet') }}
          title="Go to projects"
        >PAMET</div>
        <VerticalSeparator />

        <div
          style={{
            cursor: 'pointer'
          }}
          onClick={() => { alert('Not implemented yet') }}
          title="Project properties"
        >-default-</div>
        <img src={cloudOffIconUrl} alt="Not saved" />
        <VerticalSeparator />
        <img src={shareIconUrl} alt="Share" />
        <VerticalSeparator />
        <div
          title='Main menu'
          style={{
            fontSize: '1.2em',
            textAlign: 'center',
            cursor: 'pointer',
          }}
          onClick={() => { alert('Not implemented yet') }}
        >
          ☰
        </div>

      </Panel>

      <Panel align='top-right'>
        <img src={helpCircleIconUrl} alt="Help"
          style={{ cursor: 'pointer' }}
          onClick={() => { commands.showHelp(); }}
        />
        <VerticalSeparator />
        <div>{currentPageVS ? currentPageVS.page.name : '(no page open)'}</div>
        <VerticalSeparator />
        <img src={accountCircleIconUrl} alt="Login/Sign up" />
      </Panel>

      {/* Edit window (if open) */}
      {currentPageVS && currentPageVS.noteEditWindowState &&
        // Edit-window related.
        // The mouse event handling is tricky, since it's nicer to use the title-bar
        // onDown/Up/.. signals (we can't make the whole component transparent to
        // pointer events, since it has a lot of functionality). So we catch the
        // mouseDown and mouseUp events on the title-bar handle and trigger the
        // edit-window-drag events accodingly. Also we update the mouse state, because
        // we need to properly handle enter/leave events (and offscreen mouse release)


        <EditComponent
          state={currentPageVS.noteEditWindowState}
          onTitlebarPress={(event: React.MouseEvent) => {
            event.preventDefault();
            let mousePos = new Point2D(event.clientX, event.clientY);
            state.mouse.applyPressEvent(event);
            pageActions.startEditWindowDrag(currentPageVS, mousePos);
          }}
          onTitlebarRelease={(event: React.MouseEvent) => {
            event.preventDefault();
            state.mouse.applyReleaseEvent(event);
            pageActions.endEditWindowDrag(currentPageVS);
          }}
          onCancel={() => {
            pageActions.abortEditingNote(currentPageVS)
          }}
          onSave={(note) => {
            pageActions.saveEditedNote(currentPageVS, note)
          }}
        />
      }
    </div>
  );
});

export default WebApp;
