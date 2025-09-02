import "@/containers/app/App.css";
import "@/components/PanelLayer.css";
import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";

import { PageView } from "@/components/page/PageView";

import { getLogger } from "fusion/logging";
import { styled } from "styled-components";
import Panel from "@/components/Panel";

import cloudOffIconUrl from "@/resources/icons/cloud-off.svg";
import shareIconUrl from "@/resources/icons/share-2.svg";
import accountCircleIconUrl from "@/resources/icons/account-circle.svg";
import helpCircleIconUrl from "@/resources/icons/help-circle.svg";
import { commands, confirmPageDeletion } from "@/core/commands";
import { pageActions } from "@/actions/page";
import NoteEditView from "@/components/note/NoteEditView";
import { projectActions } from "@/actions/project";
import { CreatePageDialog } from "@/components/CreateNewPageDialog";
import { appActions } from "@/actions/app";
import { PagePropertiesDialog } from "@/components/PagePropertiesDialog";
import { ProjectPropertiesDialog } from "@/components/ProjectPropertiesDialog";
import { ProjectsDialog } from "@/components/ProjectsDialog";
import { CreateProjectDialog } from "@/components/CreateProjectDialog";
import { DebugDialog } from "@/components/DebugDialog";
import { importDesktopDataForTesting, updateAppFromRouteOrAutoassist } from "@/procedures/app";
import { WebAppState, ProjectError, PageError, AppDialogMode } from "@/containers/app/WebAppState";
import { MediaProcessingDialog } from "@/components/system-modal-dialog/LoadingDialog";
import { PageAndCommandPaletteState, ProjectPaletteState } from "@/components/CommandPaletteState";
import { PageAndCommandPalette, ProjectPalette } from "@/components/CommandPalette";
import { LocalSearch } from "@/components/search/LocalSearch";
import { GlobalSearch } from "@/components/search/GlobalSearch";
import { pamet } from "@/core/facade";
import Menu, { MenuItem } from "@/components/menu/Menu";

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
  const [showLoadingDialog, setShowLoadingDialog] = useState(false);
  const [mainMenuPos, setMainMenuPos] = useState<{x:number,y:number} | null>(null);

  // Change the title when the current page changes
  useEffect(() => {
    if (state.currentPageViewState) {
      document.title = state.currentPageViewState.page().name;
    } else {
      document.title = "Pamet";
    }
  }, [state.currentPageViewState]);

  useEffect(() => {
    // Set delayed system modal dialog visibility to avoid
    // Brief pop-up on short tasks
    const dialogState = state.loadingDialogState;
    if (!dialogState) {
      setShowLoadingDialog(false);
      return;
    }

    if (dialogState.showAfterUnixTime === null) {
      setShowLoadingDialog(true);
      return;
    }

    const now = Date.now();
    const delay = dialogState.showAfterUnixTime - now;

    if (delay <= 0) {
      setShowLoadingDialog(true);
      return;
    }

    const timer = setTimeout(() => {
      setShowLoadingDialog(true);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [state.loadingDialogState]);

  // Check for resurce availability, and prep error messages if needed
  let shouldDisplayPage = true

  if (!state.deviceId) {
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

  const getShortcut = (commandName: string): string | undefined => {
    return pamet.keybindingService?.getShortcutForCommand(commandName) || undefined;
  };

  const mainMenuItems: MenuItem[] = [
    {
      label: 'Project',
      submenu: [
        { label: 'Open Projects…', onClick: () => appActions.openProjectsDialog(state) },
        { label: 'Project Properties…', onClick: () => appActions.openProjectPropertiesDialog(state) },
        { type: 'separator', label: '' },
        { label: 'Create New Project…', onClick: () => appActions.openCreateProjectDialog(state) },
      ]
    },
    {
      label: 'Page',
      submenu: [
        { label: 'New Page…', onClick: () => commands.createNewPage(), shortcut: getShortcut(commands.createNewPage.name) },
        { label: 'Page Properties…', onClick: () => appActions.openPageProperties(state), shortcut: getShortcut(commands.openPageProperties.name) },
        { type: 'separator', label: '' },
        { label: 'Delete Page', onClick: () => commands.deleteCurrentPage() },
      ]
    },
    {
      label: 'Search',
      submenu: [
        { label: 'Local Search', onClick: () => appActions.openLocalSearch(state), shortcut: getShortcut(commands.openLocalSearch.name) },
        { label: 'Global Search', onClick: () => appActions.openGlobalSearch(state), shortcut: getShortcut(commands.openGlobalSearch.name) },
        { label: 'Command Palette', onClick: () => commands.openCommandPalette(), shortcut: getShortcut(commands.openCommandPalette.name) },
      ]
    },
    {
      label: 'View',
      submenu: [
        { label: 'Zoom In', onClick: () => commands.pageZoomIn(), shortcut: getShortcut(commands.pageZoomIn.name) },
        { label: 'Zoom Out', onClick: () => commands.pageZoomOut(), shortcut: getShortcut(commands.pageZoomOut.name) },
        { label: 'Reset Zoom', onClick: () => commands.pageZoomReset(), shortcut: getShortcut(commands.pageZoomReset.name) },
      ]
    }
  ];

  // Context menu handled within PageView directly.


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
      {shouldDisplayPage && (
        <div style={{ width: '100%', height: '100%' }}>
          <PageView state={state.currentPageViewState!} mouseState={state.mouseState} />
        </div>
      )}

      {/* Panel Layer - Grid layout for panels and sidebars */}
      <div className="panel-layer">
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
          className="project-name"
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
          onClick={(e) => {
            const target = e.currentTarget as HTMLElement;
            const panel = target.closest('.panel') as HTMLElement | null;
            const r = (panel ?? target).getBoundingClientRect();
            setMainMenuPos({ x: r.right, y: r.bottom + 6 });
          }}
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
        <VerticalSeparator />
        <div
          title='Desktop import (dbg)'
          style={{ cursor: 'pointer' }}
          onClick={() => importDesktopDataForTesting()}
        >
          {/* Use a unicode symbol for import */}
          &#x21E9;
        </div>
        <VerticalSeparator />
        <img src={helpCircleIconUrl} alt="Help"
          style={{ cursor: 'pointer' }}
          onClick={() => { commands.showHelp(); }}
        />
        <VerticalSeparator />
        <div
          onClick={() => appActions.openPageProperties(state)}
          style={{ cursor: 'pointer' }}
          title="Page properties"
        >{currentPageVS ? currentPageVS.page().name : '(no page open)'}</div>
        <VerticalSeparator />
        <img src={accountCircleIconUrl} alt="Login/Sign up" />
      </Panel>

        {/* Global search sidebar */}
        {state.globalSearchViewState &&
          <GlobalSearch state={state.globalSearchViewState} />}
      </div>

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
        />}

      {state.dialogMode === AppDialogMode.CreateNewPage && (
        <CreatePageDialog
          onClose={() => appActions.closeAppDialog(state)}
          onCreate={(name: string) => {
            log.info(`Creating new page: ${name}`);
            let page = projectActions.createNewPage(state, name)
            log.info(`Setting current page to ${name}`);
            appActions.setCurrentPage(state, page.id);

            // Open settings view | IMPLEMENT LATER
          }}
        />
      )}

      {state.dialogMode === AppDialogMode.PageProperties && state.currentPageViewState && (
        <PagePropertiesDialog
          page={state.currentPageViewState.page()}
          onClose={() => appActions.closeAppDialog(state)}
          onSave={(page) => pageActions.updatePageProperties(page)}
          onDelete={(page) => {
            if (confirmPageDeletion(page.name)) {
              projectActions.deletePageAndUpdateReferences(page);
              appActions.closeAppDialog(state);
              let route = pamet.router.currentRoute();
              route.pageId = undefined
              updateAppFromRouteOrAutoassist(route).catch((err) => {
                log.error("Error updating app from route after page deletion", err);
              });
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

      {showLoadingDialog && state.loadingDialogState && (
        <MediaProcessingDialog state={state.loadingDialogState} />
      )}
      {state.commandPaletteState instanceof PageAndCommandPaletteState &&
        <PageAndCommandPalette state={state.commandPaletteState} />}
      {state.commandPaletteState instanceof ProjectPaletteState &&
        <ProjectPalette state={state.commandPaletteState} />}
      {state.localSearchViewState &&
        <LocalSearch state={state.localSearchViewState} />}

      {(mainMenuPos) && (
        <div
          // Overlay: close menus on outside click and swallow interactions beneath
          onMouseDown={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setMainMenuPos(null);
          }}
          onMouseMove={(e) => { e.preventDefault(); e.stopPropagation(); }}
          onWheel={(e) => { e.preventDefault(); e.stopPropagation(); }}
          onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); }}
          style={{ position: 'fixed', inset: 0, zIndex: 9998 }}
        />
      )}

      {mainMenuPos && (
        <Menu
          items={mainMenuItems}
          x={mainMenuPos.x}
          y={mainMenuPos.y}
          variant='main'
          alignX='right'
          onDismiss={() => setMainMenuPos(null)}
        />
      )}

      {/* Context menu is rendered within PageView */}
    </div>
  );
});

export default WebApp;
