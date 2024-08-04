import { pageActions } from "../actions/page";
import { pamet } from "./facade";
import { command } from "fusion/libs/Command";
import { getLogger } from "fusion/logging";
import { Point2D } from "../util/Point2D";

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
        let mousePos = pageVS.realMousePositionOnCanvas;
        let creationPos: Point2D;

        if (mousePos === null) {
            creationPos = pageVS.viewport.realCenter;
        } else {
            creationPos = mousePos;
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
}

export const commands = new PametCommands();
