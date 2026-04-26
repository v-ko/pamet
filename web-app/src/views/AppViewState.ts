import { makeObservable, observable } from "mobx";
import { PageViewState } from "@/views/page/PageViewState";
import { PametProjectData, ProjectReference } from "@/model/Project";
import { Point2D } from "fusion/primitives/Point2D";
import { PametRoute } from "@/services/routing/PametRoute";
import { LoadingDialogState } from "@/views/system-modal-dialog/state";
import { CommandPaletteState } from "@/views/CommandPaletteState";
import { LocalSearchViewState } from "@/views/search/LocalSearchViewState";
import { GlobalSearchViewState } from "@/views/search/GlobalSearchViewState";
import React from "react";
import { Note } from "@/model/Note";
import { Arrow } from "@/model/Arrow";
import { StorageProxyState, createInitialStorageProxyState } from "fusion/storage/management/StorageServiceProxy";
import { ThemePreference, ThemeMode } from "@/app/theme";
import { ReplayPanelViewState } from "@/views/replay/ReplayViewState";
import { BackupPanelViewState } from "@/views/replay/BackupViewState";


export enum AppDialogMode {
  Closed,
  CreateNewPage,
  CreateNewProject,
  ProjectProperties,
  PageProperties,
  ProjectsDialog,
  StorageStatus,
}

export enum PageError {
  NoError,
  NotFound
}

export enum ProjectError {
  NoError,
  NotFound
}

export type SaveStatus = 'saved' | 'unsaved' | 'saving' | 'error';

export interface PametStorageState {
  service: StorageProxyState;
  saveStatus: SaveStatus;
}


export class AppViewState {
  deviceId: string | null = null;
  userId: string;

  currentProjectId: string | null = null;
  currentProjectState: PametProjectData | null = null;
  trackedProjects: ProjectReference[] = [];
  recentProjects: ProjectReference[] = [];
  projectError: ProjectError = ProjectError.NoError;

  currentPageId: string | null = null;
  currentPageViewState: PageViewState | null = null;
  pageError: PageError = PageError.NoError;

  storageState: PametStorageState = {
    service: createInitialStorageProxyState(),
    saveStatus: 'saved',
  };

  dialogMode: AppDialogMode = AppDialogMode.Closed;
  focusPointOnDialogOpen: Point2D = new Point2D([0, 0]); // Either the mouse location or the center of the screen
  loadingDialogState: LoadingDialogState | null = null;
  mouseState: MouseState = new MouseState();
  commandPaletteState: CommandPaletteState | null = null;
  localSearchViewState: LocalSearchViewState | null = null;
  globalSearchViewState: GlobalSearchViewState | null = null;

  // Internal clipboard for copy/cut/paste (entities stored with relative coordinates)
  clipboard: (Note | Arrow)[] = [];
  // The project ID the clipboard entities originate from (for cross-project paste)
  clipboardProjectId: string | null = null;

  devErrors: boolean = false;

  themePreference: ThemePreference = ThemePreference.Auto;
  themeResolvedMode: ThemeMode = ThemeMode.Light;

  historyPageViewState: PageViewState | null = null; // Mock so we can reuse the reducer
  replayPanelVS: ReplayPanelViewState | null = null;
  backupPanelVS: BackupPanelViewState | null = null;

  /** Clear the selected commit/backup so the history overlay hides. */
  deselectHistoryItem() {
    this.historyPageViewState = null;
    if (this.replayPanelVS) {
      this.replayPanelVS.currentMarkerIdx = -1;
    }
    if (this.backupPanelVS) {
      this.backupPanelVS.selectedBackupId = null;
    }
  }

  constructor(options: { userId: string }) {
    this.userId = options.userId;
    makeObservable(this, {
      deviceId: observable,
      userId: observable,
      currentProjectId: observable,
      currentProjectState: observable,
      trackedProjects: observable,
      recentProjects: observable,
      currentPageViewState: observable,
      storageState: observable,
      pageError: observable,
      projectError: observable,
      dialogMode: observable,
      loadingDialogState: observable,
      commandPaletteState: observable,
      localSearchViewState: observable,
      globalSearchViewState: observable,
      clipboard: observable,
      clipboardProjectId: observable,
      devErrors: observable,
      themePreference: observable,
      themeResolvedMode: observable,
      replayPanelVS: observable,
      backupPanelVS: observable,
      historyPageViewState: observable.ref,
    });
  }

  getCurrentProject(): PametProjectData {
    if (!this.currentProjectState) {
      throw new Error("No current project state set.");
    }
    return this.currentProjectState;
  }

  trackedProject(projectId: string): ProjectReference | undefined {
    return this.trackedProjects.find((project) => project.id === projectId);
  }

  pageViewState(pageId: string): PageViewState {
    // Since there's no caching just returns the current if it's the correct
    // page id. Else throws an error
    if (this.currentPageViewState && this.currentPageViewState.page().id === pageId) {
      return this.currentPageViewState;
    }
    throw new Error(`PageViewState not found for pageId: ${pageId}.`);
  }

  toRoute(): PametRoute {
    let userId = this.userId;
    let projectId = this.currentProjectId;
    let pageId = this.currentPageId;

    if (projectId === null && pageId !== null) {
      throw new Error('Page id set without project id.');
    }

    let route = new PametRoute({});

    route.userId = userId;  // Always set
    if (projectId) {
      route.projectId = projectId;
    }
    if (pageId) {
      route.pageId = pageId;
    }

    // Include viewport parameters for stable back/forward and toggling restoration
    if (this.currentPageViewState) {
      route.viewportCenter = [
        this.currentPageViewState.viewportCenter.x,
        this.currentPageViewState.viewportCenter.y
      ];
      route.viewportEyeHeight = this.currentPageViewState.viewportHeight;
    }

    return route;
  }

}

interface MouseStateData {
  buttons: number;
  position: Point2D | null;
  positionOnPress: Point2D | null;
  buttonsOnLeave: number;
}

export class MouseState {
  buttons: number = 0;
  position: Point2D | null = null;
  positionOnPress: Point2D | null = null;
  buttonsOnLeave: number = 0;

  constructor() {
    makeObservable(this, {
      position: observable,
      positionOnPress: observable,
      buttons: observable,
      buttonsOnLeave: observable,
    });
  }

  get mouseIsPresent(): boolean {
    return this.position !== null;
  }

  get rightIsPressed() {
    return (this.buttons & 2) !== 0;
  }
  get leftIsPressed() {
    return (this.buttons & 1) !== 0;
  }
  data(): MouseStateData {
    return {
      buttons: this.buttons,
      position: this.position,
      positionOnPress: this.positionOnPress,
      buttonsOnLeave: this.buttonsOnLeave
    };
  }
  applyPressEvent(event: React.MouseEvent) {
    this.positionOnPress = new Point2D([event.clientX, event.clientY]);
    this.buttons = event.buttons;
  }
  applyMoveEvent(event: React.MouseEvent) {
    this.position = new Point2D([event.clientX, event.clientY]);
  }
  applyReleaseEvent(event: React.MouseEvent) {
    this.buttons = event.buttons;
  }
}
