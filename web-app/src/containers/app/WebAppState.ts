import { makeObservable, observable } from "mobx";
import { DeviceData } from "web-app/src/model/config/Device";
import { UserData } from "web-app/src/model/config/User";
import { MouseState, PageViewState } from "web-app/src/components/page/PageViewState";
import { pamet } from "web-app/src/core/facade";
import { ProjectData } from "web-app/src/model/config/Project";
import { Point2D } from "web-app/src/util/Point2D";
import { PametRoute } from "../../services/routing/route";


export enum AppDialogMode {
  Closed,
  CreateNewPage,
  CreateNewProject,
  ProjectProperties,
  PageProperties,
  ProjectsDialog
}

export enum PageError {
  NoError,
  NotFound
}

export enum ProjectError {
  NoError,
  NotFound
}

export interface LocalStorageState {
  available: boolean;

}
export interface PametStorageState {
  localStorage: LocalStorageState;
}


export class WebAppState {
  deviceId: string | null = null;
  userId: string | null = null;

  currentProjectId: string | null = null;
  currentProjectState: ProjectData | null = null;
  projectError: ProjectError = ProjectError.NoError;

  currentPageId: string | null = null;
  currentPageViewState: PageViewState | null = null;
  pageError: PageError = PageError.NoError;

  storageState: PametStorageState = {
    localStorage: {
      available: false
    }
  };

  dialogMode: AppDialogMode = AppDialogMode.Closed;
  focusPointOnDialogOpen: Point2D = new Point2D(0, 0); // Either the mouse location or the center of the screen
  mouse: MouseState = new MouseState();

  constructor() {
    makeObservable(this, {
      deviceId: observable,
      userId: observable,
      currentProjectId: observable,
      currentProjectState: observable,
      currentPageViewState: observable,
      storageState: observable,
      pageError: observable,
      projectError: observable,
      dialogMode: observable,
    });
  }

  get device(): DeviceData | null {
    if (!this.deviceId) {
      return null;
    }
    let deviceData = pamet.config.deviceData;
    if (!deviceData) {
      throw new Error("DeviceData missing.");
    }
    return deviceData;
  }
  get user(): UserData | null {
    if (!this.userId) {
      return null;
    }
    let userData = pamet.config.userData;
    if (!userData) {
      throw new Error("UserData missing.");
    }
    return userData;
  }
  currentProject() {
    if (!this.currentProjectId) {
      return null;
    }
    let projectData = pamet.project(this.currentProjectId);
    if (!projectData) {
      throw new Error("ProjectData missing.");
    }
    return projectData;
  }

  pageViewState(pageId: string): PageViewState {
    // Since there's no caching just returns the current if it's the correct
    // page id. Else throws an error
    if (this.currentPageViewState && this.currentPageViewState.page.id === pageId) {
      return this.currentPageViewState;
    }
    throw new Error("PageViewState not found");
  }

  route(): PametRoute {
    let userId = this.userId;
    let projectId = this.currentProjectId;
    let pageId = this.currentPageId;

    if (projectId === null && pageId !== null) {
      throw new Error('Page id set without project id.');
    }

    let route = new PametRoute();
    
    if (userId) {
      route.userId = userId;
    }
    if (projectId) {
      route.projectId = projectId;
    }
    if (pageId) {
      route.pageId = pageId;
    }

    return route;
  }

}
