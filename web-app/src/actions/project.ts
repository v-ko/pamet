import { action } from "fusion/registries/Action";
import { AppDialogMode, AppViewState } from "@/views/AppViewState";
import { pamet } from "@/app/facade";
import { Page, PageData } from "@/model/Page";
import { currentTime, timestamp } from "fusion/util/base";
import { minimalNonelidedSize } from "@/views/note/note-dependent-utils";
import { Point2D } from "fusion/primitives/Point2D";
import { getEntityId } from "fusion/model/Entity";
import { snapVectorToGrid } from "@/app/util";
import { CardNote } from "@/model/CardNote";
import { CANVAS_EXT } from "@/app/constants";
import {
    linkUpdatesForPageDelete,
    imageReassignmentUpdatesForPageDelete,
} from '@/model/correctness';


class ProjectActions {

  @action({ issuer: 'service' })
  createNewPageWithHelpNote(): Page {
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

    return page;
  }

  @action
  setHomePage(appViewState: AppViewState, pageId: string) {
    let projectData = appViewState.getCurrentProject();
    pamet.saveProjectProperties({
      ...projectData,
      home_page_id: pageId,
    });
  }

  @action
  openPageCreationDialog(appViewState: AppViewState, forwardLinkLocation: Point2D) {
    appViewState.dialogMode = AppDialogMode.CreateNewPage;
    appViewState.focusPointOnDialogOpen = forwardLinkLocation;
  }

  @action
  createNewPage(appViewState: AppViewState, name: string): Page {
    if (!appViewState.currentPageViewState) {
      throw Error('No current page. Cannot create a new page via createNewPage. Use createNewPageWithHelpNote instead.')
    }
    let forwardLinkLocation = snapVectorToGrid(appViewState.focusPointOnDialogOpen);

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
    let currentPage = appViewState.currentPageViewState.page()
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
  openPageProperties(state: AppViewState) {
    state.dialogMode = AppDialogMode.PageProperties;
  }

  @action
  deletePageAndUpdateReferences(page: Page) {
    const store = pamet.currentProjectStore;

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
    if (currentProject?.home_page_id === page.id) {
      pamet.saveProjectProperties({
        ...currentProject,
        home_page_id: undefined,
      });
    }

    // Apply link-deletion markers
    for (const u of linkUpdates) {
      pamet.updateNote(u.updated);
    }
  }
}

export const projectActions = new ProjectActions();
