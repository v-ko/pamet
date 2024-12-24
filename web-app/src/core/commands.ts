import { pageActions } from "../actions/page";
import { pamet } from "./facade";
import { command } from "fusion/libs/Command";
import { getLogger } from "fusion/logging";
import { Point2D } from "../util/Point2D";
import { arrowActions } from "../actions/arrow";
import { projectActions } from "../actions/project";
import { Note } from "../model/Note";
import { NoteViewState } from "../components/note/NoteViewState";
import { PageViewState } from "../components/page/PageViewState";

let log = getLogger('PametCommands');


function getCurrentPageViewState(): PageViewState {
    let appState = pamet.appViewState;
    let pageVS = appState.currentPageViewState;
    if (pageVS === null) {
        throw Error('No current page view state');
    }
    return pageVS;
}

class PametCommands {
    @command('Create new note')
    createNewNote() {
        console.log('createNewNote command executed')

        // Get the real mouse pos on canvas (if it's over the viewport)
        let pageVS = getCurrentPageViewState();
        let mousePos = pageVS.projectedMousePosition;
        let creationPos: Point2D;

        if (mousePos === null) {
            creationPos = pageVS.viewport.realCenter;
        } else {
            creationPos = pageVS.viewport.unprojectPoint(mousePos);
        }

        // Create a new note
        pageActions.startNoteCreation(pageVS, creationPos);
    }

    @command('Auto-size selected notes')
    autoSizeSelectedNotes() {
        let pageVS = getCurrentPageViewState();
        pageActions.autoSizeSelectedNotes(pageVS);
    }

    @command('Delete selected notes and arrows')
    deleteSelectedElements() {
        let pageVS = getCurrentPageViewState();
        pageActions.deleteSelectedElements(pageVS);
    }

    @command('Set default color to selected elements')
    colorSelectedElementsPrimary() {
        let pageVS = getCurrentPageViewState();
        pageActions.colorSelectedNotes(pageVS, 'onPrimary', 'primary');
        pageActions.colorSelectedArrows(pageVS, 'onPrimary');
        pageActions.clearSelection(pageVS);
    }

    @command('Set attention color to selected elements')
    colorSelectedElementsError() {
        let pageVS = getCurrentPageViewState();
        pageActions.colorSelectedNotes(pageVS, 'onError', 'error');
        pageActions.colorSelectedArrows(pageVS, 'onError');
        pageActions.clearSelection(pageVS);
    }

    @command('Set success color to selected elements')
    colorSelectedElementsSuccess() {
        let pageVS = getCurrentPageViewState();
        pageActions.colorSelectedNotes(pageVS, 'onSuccess', 'success');
        pageActions.colorSelectedArrows(pageVS, 'onSuccess');
        pageActions.clearSelection(pageVS);
    }

    @command('Set neutral color to selected elements')
    colorSelectedElementsSurfaceDim() {
        let pageVS = getCurrentPageViewState();
        pageActions.colorSelectedNotes(pageVS, 'onSurface', 'surfaceDim');
        pageActions.colorSelectedArrows(pageVS, 'onSurface');
        pageActions.clearSelection(pageVS);
    }

    @command('Set transparent background to selected notes')
    setNoteBackgroundToTransparent() {
        let pageVS = getCurrentPageViewState();
        pageActions.colorSelectedNotes(pageVS, null, 'transparent');
        pageActions.clearSelection(pageVS);
    }

    @command('Create arrow')
    createArrow() {
        let pageVS = getCurrentPageViewState();
        arrowActions.startArrowCreation(pageVS);
    }

    @command('Show help')
    showHelp() {
        alert('Help screen not implemented yet, lol. Right-click drag or two-finger drag to navigate. N for new note. E for edit. Click to select note, drag to move. L for link creation.')
    }

    @command('Create new page')
    createNewPage() {
        let appState = pamet.appViewState;

        // Determine forward link location - either under mouse or
        // in the center of the viewport
        // Get the real mouse pos on canvas (if it's over the viewport)
        let pageVS = getCurrentPageViewState();
        let mousePos = pageVS.projectedMousePosition;
        let forwardLinkLocation: Point2D;
        if (mousePos === null) {
            forwardLinkLocation = pageVS.viewport.realCenter;
        } else {
            forwardLinkLocation = pageVS.viewport.unprojectPoint(mousePos);
        }

        projectActions.openPageCreationDialog(appState, forwardLinkLocation);
    }

    @command('Edit note')
    editSelectedNote() {
        let pageVS = getCurrentPageViewState();

        // Start editing the selected note
        let selectedNote: Note | null = null;
        for (let elementVS of pageVS.selectedElementsVS.values()) {
            if (elementVS instanceof NoteViewState) {
                selectedNote = elementVS.note();
                break;
            }
        }
        if (selectedNote !== null) {
            pageActions.startEditingNote(pageVS, selectedNote);
        }
    }

    @command('Cancel page action')
    cancelPageAction() {
        pageActions.clearMode(getCurrentPageViewState());
    }

    @command('Page: Zoom in')
    pageZoomIn() {
        let pageVS = getCurrentPageViewState();
        pageActions.updateViewport(pageVS, pageVS.viewportCenter, pageVS.viewportHeight / 1.1);
    }

    @command('Page: Zoom out')
    pageZoomOut() {
        let pageVS = getCurrentPageViewState();
        pageActions.updateViewport(pageVS, pageVS.viewportCenter, pageVS.viewportHeight * 1.1);
    }

    @command('Page: Reset zoom')
    pageZoomReset() {
        let pageVS = getCurrentPageViewState();
        pageActions.updateViewport(pageVS, pageVS.viewportCenter, 1);
    }

    @command('Select all')
    selectAll() {
        let pageVS = getCurrentPageViewState();
        // Select all
        let selectionMap = new Map();
        for (let noteVS of pageVS.noteViewStatesByOwnId.values()) {
            selectionMap.set(noteVS, true);
        }
        for (let arrowVS of pageVS.arrowViewStatesByOwnId.values()) {
            selectionMap.set(arrowVS, true);
        }
        pageActions.updateSelection(pageVS, selectionMap);
    }
}

export const commands = new PametCommands();
