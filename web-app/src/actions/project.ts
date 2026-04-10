import { action } from "fusion/registries/Action";
import { AppDialogMode, WebAppState } from "@/containers/app/WebAppState";
import { pamet } from "@/core/facade";
import { Page, PageData } from "@/model/Page";
import { currentTime, timestamp } from "fusion/util/base";
import { minimalNonelidedSize } from "@/components/note/note-dependent-utils";
import { Point2D } from "fusion/primitives/Point2D";
import { getEntityId } from "fusion/model/Entity";
import { snapVectorToGrid } from "@/util";
import type { PametProjectData } from "@/model/Project";
import { getLogger } from "fusion/logging";
import { appActions } from "@/actions/app";
import { CardNote } from "@/model/CardNote";
import { CANVAS_EXT } from "@/core/constants";
import {
    linkUpdatesForPageDelete,
    imageReassignmentUpdatesForPageDelete,
} from '@/model/correctness';

const log = getLogger("ProjectActions");


class ProjectActions {

  @action
  updateProject(projectData: PametProjectData) {
    void pamet.saveProjectProperties(projectData).catch((error) => {
      log.error("Failed to save project properties", error);
    });
  }

  @action({ issuer: 'service' })
  createDefaultPage(appState: WebAppState) {
    // Create the page
    const currentTimestamp = timestamp(currentTime())
    let pageData: PageData = {
      path: 'Home Page' + CANVAS_EXT,
      id: getEntityId(),
      parent_id: '',
      created: currentTimestamp,
      modified: currentTimestamp,
    }
    let page = new Page(pageData)
    pamet.insertPage(page)

    // Add a "Press H for help" note in the center
    let note = CardNote.createNew({ pageId: page.id })
    note.content.text = 'Press H for help'
    let noteRect = note.rect()
    noteRect.setSize(minimalNonelidedSize(note))
    noteRect.moveCenter(new Point2D([0, 0]))
    note.setRect(noteRect)
    pamet.insertNote(note)

    // Set page as default for the project
    let projectData = appState.getCurrentProject();
    this.updateProject({
      ...projectData,
      default_page_id: page.id,
    });
  }

  @action
  openPageCreationDialog(appState: WebAppState, forwardLinkLocation: Point2D) {
    appState.dialogMode = AppDialogMode.CreateNewPage;
    appState.focusPointOnDialogOpen = forwardLinkLocation;
  }

  @action
  createNewPage(appState: WebAppState, name: string): Page {
    if (!appState.currentPageViewState) {
      throw Error('No current page. Cannot create a new page via createNewPage. Use createDefaultPage instead.')
    }
    let forwardLinkLocation = snapVectorToGrid(appState.focusPointOnDialogOpen);

    let currentTimestamp = timestamp(currentTime());
    let newPage = new Page({
      path: name + CANVAS_EXT,
      id: getEntityId(),
      parent_id: '', // Pages are project scoped and don't need to point to a parent for now
      created: currentTimestamp,
      modified: currentTimestamp,
    })
    pamet.insertPage(newPage)

    // Create a forward link note on the given location in the current page
    let currentPage = appState.currentPageViewState.page()
    let forwardLink = CardNote.createInternalLinkNote(newPage, currentPage.id)
    // Autosize and set at location
    let minimalSize = minimalNonelidedSize(forwardLink);
    let rect = forwardLink.rect();
    let newSize = snapVectorToGrid(minimalSize)
    rect.setSize(newSize);
    rect.setTopLeft(forwardLinkLocation);
    forwardLink.setRect(rect);
    pamet.insertNote(forwardLink);

    // Create a back link note in the new page (to the current)
    let backLink = CardNote.createInternalLinkNote(currentPage, newPage.id)
    // Autosize and set at center
    rect = backLink.rect();
    const backMinimalSize = minimalNonelidedSize(backLink);
    rect.setSize(backMinimalSize);
    rect.moveCenter(new Point2D([0, 0]));
    backLink.setRect(rect);
    pamet.insertNote(backLink);

    return newPage;
  }

  @action
  openPageProperties(state: WebAppState) {
    state.dialogMode = AppDialogMode.PageProperties;
  }

  @action
  deletePageAndUpdateReferences(page: Page) {
    const store = pamet.frontendDomainStore;

    // Compute all reference-fixup updates before mutating
    const imageUpdates = imageReassignmentUpdatesForPageDelete(store, page.id);
    const linkUpdates = linkUpdatesForPageDelete(store, page.id, page.name);

    // Apply image reassignments
    for (const u of imageUpdates) {
      pamet.updateOne(u.updated);
    }

    // Delete the page and its contents
    pamet.removePageWithChildren(page);

    const currentProject = pamet.appViewState.currentProjectState;
    if (currentProject?.default_page_id === page.id) {
      this.updateProject({
        ...currentProject,
        default_page_id: undefined,
      });
    }

    // Apply link-deletion markers
    for (const u of linkUpdates) {
      pamet.updateNote(u.updated);
    }
  }

  @action
  goToDefaultPage(appState: WebAppState) {
    const projectData = appState.getCurrentProject();
    const defaultPageId = projectData.default_page_id;

    if (defaultPageId) {
      appActions.setCurrentPage(appState, defaultPageId);
    } else {
      let firstPage = pamet.pages().next().value;
      if (firstPage) {
        appActions.setCurrentPage(appState, firstPage.id);
      } else {
        appState.currentPageId = null;
        appState.currentPageViewState = null;
      }
    }
  }
}

export const projectActions = new ProjectActions();
