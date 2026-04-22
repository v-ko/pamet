import "@/views/App.css";
import "@/views/PanelLayer.css";
import { useEffect, useState } from "react";
import { observer } from "mobx-react-lite";
import { ThemePreference } from "@/app/theme";

import { PageView } from "@/views/page/PageView";

import { getLogger } from "fusion/logging";
import { styled } from "styled-components";
import Panel from "@/views/Panel";

import shareIconUrl from "@/resources/icons/share-2.svg";
import accountCircleIconUrl from "@/resources/icons/account-circle.svg";
import helpCircleIconUrl from "@/resources/icons/help-circle.svg";
import { confirmPageDeletion } from "@/app/commands";
import { commands } from "@/app/commands";
import { pageActions } from "@/actions/page";
import NoteEditView from "@/views/note/NoteEditView";
import { CreatePageDialog } from "@/views/dialogs/CreateNewPageDialog";
import { appActions } from "@/actions/app";
import { deletePageAndNavigate, createPageAndNavigate } from "@/procedures/app";
import { PagePropertiesDialog } from "@/views/dialogs/PagePropertiesDialog";
import { ProjectPropertiesDialog } from "@/views/dialogs/ProjectPropertiesDialog";
import { ProjectsDialog } from "@/views/dialogs/ProjectsDialog";
import { CreateProjectDialog } from "@/views/dialogs/CreateProjectDialog";
import { DebugDialog } from "@/views/dialogs/DebugDialog";


import { AppViewState, ProjectError, PageError, AppDialogMode } from "@/views/AppViewState";
import { MediaProcessingDialog } from "@/views/system-modal-dialog/LoadingDialog";
import { pamet } from "@/app/facade";
import { PageAndCommandPaletteState, ProjectPaletteState } from "@/views/CommandPaletteState";
import { PageAndCommandPalette, ProjectPalette } from "@/views/CommandPalette";
import { LocalSearch } from "@/views/search/LocalSearch";
import { GlobalSearch } from "@/views/search/GlobalSearch";
import { PametTabIndex } from "@/app/constants";
import Menu, { MenuItem } from "@/views/menu/Menu";
import { StorageStatusDialog } from "@/views/dialogs/StorageStatusDialog";

let log = getLogger("App");

// Vertical line component
const VerticalSeparator = styled.div`
  width: 1px;
  height: 1em;
  background: var(--color-light-border);
`

const WebApp = observer(({ state }: { state: AppViewState }) => {
  let errorMessages: string[] = []
  const [debugInfoModalOpen, setDebugInfoModalOpen] = useState(false);
  const [showLoadingDialog, setShowLoadingDialog] = useState(false);
  const [mainMenuPos, setMainMenuPos] = useState<{ x: number, y: number } | null>(null);

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

  // Check for resource availability, and prep error messages if needed
  let shouldDisplayPage = true

  if (!state.deviceId) {
    errorMessages.push('DeviceData missing. This is a pretty critical error.')
  }
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
  const storageConnectionPhase = state.storageState.service.connectionPhase;
  const storageDegraded = state.storageState.service.degraded;
  const saveStatus = state.storageState.saveStatus;
  const storageStatusIconUrl = pamet.getStorageStatusIconUrl(storageConnectionPhase, storageDegraded, saveStatus);

  const storageStatusTitle = (() => {
    switch (storageConnectionPhase) {
      case 'ready':
        return 'Storage connected';
      case 'connecting':
        return 'Storage connecting';
      case 'disconnected':
        return 'Storage disconnected';
      case 'fatal':
        return 'Storage error';
      default:
        return 'Storage status';
    }
  })();

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
        { type: 'separator', label: '' },
        {
          label: 'Appearance',
          submenu: [
            {
              label: 'Light Mode',
              onClick: () => commands.switchToLightMode(),
              disabled: pamet.appViewState.themePreference === ThemePreference.Light,
            },
            {
              label: 'Dark Mode',
              onClick: () => commands.switchToDarkMode(),
              disabled: pamet.appViewState.themePreference === ThemePreference.Dark,
            },
            {
              label: 'Match System',
              onClick: () => commands.matchSystemColorScheme(),
              disabled: pamet.appViewState.themePreference === ThemePreference.Auto,
            },
          ],
        },
      ]
    }
  ];

  // Context menu handled within PageView directly.


  return (
    <div className="app">
      {/* a div for the app messages to be displayed in the center of the screen */}
      {/* use only inline css */}
      <div className="app-error-overlay">

        {/* Display messages */}
        {errorMessages.map((message, index) => (
          <div key={index}>{message}</div>
        ))}
      </div>


      {/* If page data - display the page */}
      {shouldDisplayPage && (
        <div className="page-container">
          <PageView state={state.currentPageViewState!} mouseState={state.mouseState} />
        </div>
      )}

      {/* Panel Layer - Grid layout for panels and sidebars */}
      <div className="panel-layer">
        {/* Main panel - logo, project name, save state, help button */}
        <Panel align='top-left'>

          <button
            className="panel-button"
            onClick={() => appActions.openProjectsDialog(state)}
            title="Go to projects"
            tabIndex={PametTabIndex.Panel_Projects}
          >PAMET</button>
          <VerticalSeparator />

          <button
            className="panel-button project-name"
            onClick={() => appActions.openProjectPropertiesDialog(state)}
            title="Project properties"
            tabIndex={PametTabIndex.Panel_ProjectProperties}
          >{state.currentProjectState ? state.currentProjectState.title : '(no project open)'}</button>
          <button
            title={storageDegraded ? `${storageStatusTitle} (degraded)` : storageStatusTitle}
            onClick={() => appActions.openStorageStatusDialog(state)}
            tabIndex={PametTabIndex.Panel_StorageStatus}
            className="panel-button panel-button-with-badge"
          >
            <img
              src={storageStatusIconUrl}
              alt="Storage status"
              className={(storageConnectionPhase === 'disconnected' || storageConnectionPhase === 'fatal' || storageDegraded) ? 'storage-icon-error' : undefined}
            />
            {storageDegraded && (
              <span className="status-badge" />
            )}
          </button>
          <VerticalSeparator />
          <button
            className="panel-button"
            onClick={() => alert('Share — not yet implemented')}
            title="Share"
            tabIndex={PametTabIndex.Panel_Share}
          ><img src={shareIconUrl} alt="Share" /></button>
          <VerticalSeparator />
          <button
            className="panel-button"
            title='Main menu'
            tabIndex={PametTabIndex.Panel_MainMenu}
            onClick={(e) => {
              const target = e.currentTarget as HTMLElement;
              const panel = target.closest('.panel') as HTMLElement | null;
              const r = (panel ?? target).getBoundingClientRect();
              setMainMenuPos({ x: r.right, y: r.bottom + 6 });
            }}
          >
            ☰
          </button>

        </Panel>

        <Panel align='top-right'>
          <button
            title='Debug info'
            onClick={() => setDebugInfoModalOpen(!debugInfoModalOpen)}
            tabIndex={PametTabIndex.Panel_Debug}
            className="panel-button panel-button-with-badge"
          >
            {'</>'}
            {state.devErrors && (
              <span className="dev-error-badge" />
            )}
          </button>
          <VerticalSeparator />
          <button
            className="panel-button"
            title="Help"
            onClick={() => { commands.showHelp(); }}
            tabIndex={PametTabIndex.Panel_Help}
          >
            <img src={helpCircleIconUrl} alt="Help" />
          </button>
          <VerticalSeparator />
          <button
            className="panel-button"
            onClick={() => appActions.openPageProperties(state)}
            title="Page properties"
            tabIndex={PametTabIndex.Panel_PageProperties}
          >{currentPageVS ? currentPageVS.page().name : '(no page open)'}</button>
          <VerticalSeparator />
          <button
            className="panel-button"
            onClick={() => alert('Login / Sign up — not yet implemented')}
            title="Login/Sign up"
            tabIndex={PametTabIndex.Panel_Account}
          ><img src={accountCircleIconUrl} alt="Login/Sign up" /></button>
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
            createPageAndNavigate(state, name)
              .catch((e) => log.error('Error creating/navigating to new page', e));
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
              deletePageAndNavigate(state, page)
                .catch((e) => log.error('Error deleting/navigating after page deletion', e));
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

      {state.dialogMode === AppDialogMode.StorageStatus && (
        <StorageStatusDialog
          state={state}
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
          className="menu-backdrop"
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
