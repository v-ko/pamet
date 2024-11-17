import { pageActions } from "../actions/page";
import { pamet } from "./facade";
import { command } from "fusion/libs/Command";
import { getLogger } from "fusion/logging";
import { Point2D } from "../util/Point2D";
import { arrowActions } from "../actions/arrow";

let log = getLogger('PametCommands');


class PametCommands {
    @command('Create new note')
    createNewNote() {
        console.log('createNewNote command executed')

        // Get the real mouse pos on canvas (if it's over the viewport)
        let pageVS = pamet.appViewState.currentPageViewState;
        if (pageVS === null) {
            log.error('Trying to create a note with not page view state');
            return;
        }
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
        console.log('autoSizeSelectedNotes command executed')
        let pageVS = pamet.appViewState.currentPageViewState;
        if (pageVS === null) {
            log.error('Trying to auto-size notes with no page view state');
            return;
        }
        pageActions.autoSizeSelectedNotes(pageVS);
    }

    @command('Delete selected notes and arrows')
    deleteSelectedNotesAndArrows() {
        console.log('deleteSelectedNotesAndArrows command executed')
        let pageVS = pamet.appViewState.currentPageViewState;
        if (pageVS === null) {
            log.error('Trying to delete notes with no page view state');
            return;
        }
        pageActions.deleteSelectedElements(pageVS);
    }

    @command('Set default color to selected elements')
    colorSelectedElementsPrimary() {
        console.log('colorSelectedElementsPrimary command executed')
        let pageVS = pamet.appViewState.currentPageViewState;
        if (pageVS === null) {
            log.error('Trying to color notes with no page view state');
            return;
        }
        pageActions.colorSelectedNotes(pageVS, 'onPrimary', 'primary');
        pageActions.colorSelectedArrows(pageVS, 'primary');
        pageActions.clearSelection(pageVS);
    }

    @command('Set attention color to selected elements')
    colorSelectedElementsError() {
        console.log('colorSelectedElementsError command executed')
        let pageVS = pamet.appViewState.currentPageViewState;
        if (pageVS === null) {
            log.error('Trying to color notes with no page view state');
            return;
        }
        pageActions.colorSelectedNotes(pageVS, 'onError', 'error');
        pageActions.colorSelectedArrows(pageVS, 'error');
        pageActions.clearSelection(pageVS);
    }

    @command('Set success color to selected elements')
    colorSelectedElementsSuccess() {
        console.log('colorSelectedElementsSuccess command executed')
        let pageVS = pamet.appViewState.currentPageViewState;
        if (pageVS === null) {
            log.error('Trying to color notes with no page view state');
            return;
        }
        pageActions.colorSelectedNotes(pageVS, 'onSuccess', 'success');
        pageActions.colorSelectedArrows(pageVS, 'success');
        pageActions.clearSelection(pageVS);
    }

    @command('Set neutral color to selected elements')
    colorSelectedElementsSurfaceDim() {
        console.log('colorSelectedElementsSurfaceDim command executed')
        let pageVS = pamet.appViewState.currentPageViewState;
        if (pageVS === null) {
            log.error('Trying to color notes with no page view state');
            return;
        }
        pageActions.colorSelectedNotes(pageVS, 'onSurface', 'surfaceDim');
        pageActions.colorSelectedArrows(pageVS, 'surfaceDim');
        pageActions.clearSelection(pageVS);
    }

    @command('Set transparent background to selected notes')
    setNoteBackgroundToTransparent() {
        console.log('colorSelectedNotesTransparent command executed')
        let pageVS = pamet.appViewState.currentPageViewState;
        if (pageVS === null) {
            log.error('Trying to color notes with no page view state');
            return;
        }
        pageActions.colorSelectedNotes(pageVS, null, 'transparent');
        pageActions.clearSelection(pageVS);
    }

    @command('Create arrow')
    createArrow() {
        console.log('createArrow command executed')
        let pageVS = pamet.appViewState.currentPageViewState;
        if (pageVS === null) {
            log.error('Trying to create arrow with no page view state');
            return;
        }
        arrowActions.startArrowCreation(pageVS);
    }
}

export const commands = new PametCommands();
