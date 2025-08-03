import "./App.css";
import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";

import { PageView } from "../../components/page/PageView";

import { getLogger } from "fusion/logging";
import { styled } from "styled-components";
import Panel from "../../components/Panel";

import cloudOffIconUrl from '../../resources/icons/cloud-off.svg';
import shareIconUrl from '../../resources/icons/share-2.svg';
import accountCircleIconUrl from '../../resources/icons/account-circle.svg';
import helpCircleIconUrl from '../../resources/icons/help-circle.svg';
import { commands, confirmPageDeletion } from "../../core/commands";
import { pageActions } from "../../actions/page";
import NoteEditView from "../../components/note/NoteEditView";
import { Point2D } from "../../util/Point2D";
import { projectActions } from "../../actions/project";
import { CreatePageDialog } from "../../components/CreateNewPageDialog";
import { appActions } from "../../actions/app";
import { PagePropertiesDialog } from "../../components/PagePropertiesDialog";
import { ProjectPropertiesDialog } from "../../components/ProjectPropertiesDialog";
import { ProjectsDialog } from "../../components/ProjectsDialog";
import { CreateProjectDialog } from "../../components/CreateProjectDialog";
import { DebugDialog } from "../../components/DebugDialog";
import { WebAppState, ProjectError, PageError, AppDialogMode } from "./WebAppState";

let log = getLogger("App");

// Vertical line component
const VerticalSeparator = styled.div`
  width: 1px;
  height: 1em;
  background: rgba(0,0,0,0.2);
`

const WebApp = observer(({ state }: { state: WebAppState }) => {
  let errorMessages: string[] = []
  const [debugInfoModalOpen, setDebugInfoModalOpen] = useState(false);

  // Change the title when the current page changes
  useEffect(() => {
    if (state.currentPageViewState) {
      document.title = state.currentPageViewState.page.name;
    } else {
      document.title = "Pamet";
    }
  }, [state.currentPageViewState]);

  // Check for resurce availability, and prep error messages if needed
  let shouldDisplayPage = true

  if (!state.device) {
    errorMessages.push('DeviceData missing. This is a pretty critical error.')
  }
  // let localStorageAvailable = state.storageState.localStorage.available;
  // if (!localStorageAvailable) {
  //   errorMessages.push("Local storage not initialized/available.")
  //   shouldDisplayPage = false
  // }
  if (state.currentPageViewState === null) {
    shouldDisplayPage = false
  }

  if (state.projectError === ProjectError.NotFound) {
    errorMessages.push("Project not found")
    shouldDisplayPage = false
  } else {
    if (state.pageError === PageError.NotFound) {
      errorMessages.push("Page not found")
      shouldDisplayPage = false
    }

    if (state.currentPageViewState === null && state.pageError === PageError.NoError) {
      errorMessages.push("Page not set")
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
          onClick={() => appActions.openProjectsDialog(state)}
          title="Go to projects"
        >PAMET</div>
        <VerticalSeparator />

        <div
          style={{
            cursor: 'pointer'
          }}
          onClick={() => appActions.openProjectPropertiesDialog(state)}
          title="Project properties"
        >{state.currentProjectState ? state.currentProjectState.title : '(no project open)'}</div>
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
        <div
          title='Debug info'
          onClick={() => setDebugInfoModalOpen(!debugInfoModalOpen)}
        >
          {'</>'}
        </div>
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


        <NoteEditView
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
            pageActions.closeNoteEditWindow(currentPageVS)
          }}
          onSave={(note) => {
            pageActions.saveEditedNote(currentPageVS, note)
          }}
        />}

      {state.dialogMode === AppDialogMode.CreateNewPage && (
        <CreatePageDialog
          onClose={() => appActions.closeAppDialog(state)}
          onCreate={(name: string) => projectActions.createNewPage(state, name)}
        />
      )}

      {state.dialogMode === AppDialogMode.PageProperties && state.currentPageViewState && (
        <PagePropertiesDialog
          page={state.currentPageViewState.page}
          onClose={() => appActions.closeAppDialog(state)}
          onSave={(page) => pageActions.updatePageProperties(page)}
          onDelete={(page) => {
            if (confirmPageDeletion(page.name)) {
              projectActions.deletePageAndUpdateReferences(page);
            }
          }}
        />
      )}

      {state.dialogMode === AppDialogMode.ProjectProperties && state.currentProjectState && (
        <ProjectPropertiesDialog
          project={state.currentProjectState}
          onClose={() => appActions.closeAppDialog(state)}
        />
      )}

      {state.dialogMode === AppDialogMode.ProjectsDialog && (
        <ProjectsDialog
          onClose={() => appActions.closeAppDialog(state)}
        />
      )}

      {state.dialogMode === AppDialogMode.CreateNewProject && (
        <CreateProjectDialog
          onClose={() => appActions.closeAppDialog(state)}
        />
      )}

      {/* Debug Dialog */}
      <DebugDialog
        isOpen={debugInfoModalOpen}
        onClose={() => setDebugInfoModalOpen(false)}
      />
    </div>
  );
});

export default WebApp;
