import { action } from "fusion/libs/Action";
import { AppDialogMode, WebAppState } from "../containers/app/App";
import { pamet } from "../core/facade";
import { Page, PageData } from "../model/Page";
import { currentTime, timestamp } from "fusion/util";
import { minimalNonelidedSize } from "../components/note/util";
import { TextNote } from "../model/TextNote";
import { Point2D } from "../util/Point2D";
import { InternalLinkNote } from "../model/InternalLinkNote";
import { getEntityId } from "fusion/libs/Entity";
import { snapVectorToGrid } from "../util";


class ProjectActions {
    @action({ issuer: 'service' })
    createDefaultPage(appState: WebAppState) {
        // Create the page
        const currentTimestamp = timestamp(currentTime())
        let pageData: PageData = {
            name: 'Home Page',
            id: getEntityId(),
            created: currentTimestamp,
            modified: currentTimestamp,
        }
        let page = new Page(pageData)
        pamet.insertPage(page)

        // Add a "Press H for help" note in the center
        let note = TextNote.createNew(page.id)
        note.content.text = 'Press H for help'
        let noteRect = note.rect()
        noteRect.setSize(minimalNonelidedSize(note))
        noteRect.moveCenter(new Point2D(0, 0))  
        note.setRect(noteRect)
        pamet.insertNote(note)

        // Set page as default for the project
        let projectData = appState.currentProject
        if (!projectData) {
            throw Error('No current project')
        }
        projectData.defaultPageId = page.id
        pamet.updateProject(projectData)
    }

    @action
    openPageCreationDialog(appState: WebAppState, forwardLinkLocation: Point2D) {
        appState.dialogMode = AppDialogMode.CreateNewPage;
        appState.focusPointOnDialogOpen = forwardLinkLocation;
    }

    @action
    createNewPage(appState: WebAppState, name: string) {
        if (!appState.currentPageViewState) {
            throw Error('No current page. Cannot create a new page via createNewPage. Use createDefaultPage instead.')
        }
        let forwardLinkLocation = snapVectorToGrid(appState.focusPointOnDialogOpen);

        let currentTimestamp = timestamp(currentTime());
        let newPage = new Page({
            name: name,
            id: getEntityId(),
            created: currentTimestamp,
            modified: currentTimestamp,
        })
        pamet.insertPage(newPage)

        // Create a forward link note on the given location in the current page
        let currentPage = appState.currentPageViewState.page
        let forwardLink = InternalLinkNote.createNew(currentPage.id, newPage.id)
        // Autosize and set at location
        let minimalSize = minimalNonelidedSize(forwardLink);
        let rect = forwardLink.rect();
        let newSize = snapVectorToGrid(minimalSize)
        rect.setSize(newSize);
        rect.setTopLeft(forwardLinkLocation);
        forwardLink.setRect(rect);
        pamet.insertNote(forwardLink);

        // Create a back link note in the new page (to the current)
        let backLink = InternalLinkNote.createNew(newPage.id, currentPage.id)
        // Autosize and set at center
        rect = backLink.rect();
        rect.setSize(minimalSize);
        rect.moveCenter(new Point2D(0, 0));
        backLink.setRect(rect);
        pamet.insertNote(backLink);

        // Switch to new page

        // Open settings view | IMPLEMENT LATER
    }

    @action
    openPageProperties(state: WebAppState) {
        state.dialogMode = AppDialogMode.PageProperties;
    }


  @action
  deletePageAndUpdateReferences(page: Page) {
    // Delete the page and its contents
    pamet.removePageWithChildren(page);

    // Find all internal link notes pointing to this page
    const internalLinks = Array.from(pamet.find({
      type: InternalLinkNote
    }) as Generator<InternalLinkNote>).filter((note: InternalLinkNote) => note.targetPageId() === page.id);

    // Convert each internal link to a text note showing the page was removed
    for (const link of internalLinks) {
      const textNote = new TextNote({
        ...link.data(),
        content: {
          text: `(page "${page.name}" removed)`
        }
      });
      pamet.updateNote(textNote);
    }
  }
}

export const projectActions = new ProjectActions();
