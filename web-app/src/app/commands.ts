import { pageActions } from "@/actions/page";
import { pamet } from "@/app/facade";
import { command } from "fusion/registries/Command";
import { getLogger } from "fusion/logging";
import { appActions } from "@/actions/app";
import { Point2D } from "fusion/primitives/Point2D";
import { arrowActions } from "@/actions/arrow";
import { projectActions } from "@/actions/project";
import { Note } from "@/model/Note";
import { NoteViewState } from "@/views/note/NoteViewState";
import { PageViewState } from "@/views/page/PageViewState";
import { buildHashTree } from "fusion/storage/version-control/HashTree";
import { Rectangle } from "fusion/primitives/Rectangle";
import { parseClipboardContents } from "@/app/util";
import { pasteSpecial as pasteSpecialProcedure, pasteInternal as pasteInternalProcedure, cutInternal as cutInternalProcedure } from "@/procedures/page";
import { DEFAULT_VIEW_HEIGHT } from "@/app/constants";
import { PametRoute } from "@/services/routing/PametRoute";

let log = getLogger('PametCommands');

export function confirmPageDeletion(pageName: string): boolean {
    return window.confirm(`Are you sure you want to delete the page "${pageName}"?`);
}

function getCurrentPageViewState(): PageViewState {
    let appViewState = pamet.appViewState;
    let pageVS = appViewState.currentPageViewState;
    if (pageVS === null) {
        throw Error('No current page view state');
    }
    return pageVS;
}

// Shared utility: compute anchor for copy/cut commands
function computeSelectionAnchor(selectedNotes: Note[], mousePosPix: Point2D | null, pageVS: PageViewState): Point2D {
    if (selectedNotes.length === 0) {
        return pageVS.viewport.realCenter();
    }
    if (selectedNotes.length === 1) {
        return selectedNotes[0].rect().topLeft();
    }

    // Combined rect of selected notes
    let minX = Number.POSITIVE_INFINITY, minY = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY, maxY = Number.NEGATIVE_INFINITY;

    for (const note of selectedNotes) {
        const r = note.rect();
        const tl = r.topLeft();
        const br = r.bottomRight();
        if (tl.x < minX) minX = tl.x;
        if (tl.y < minY) minY = tl.y;
        if (br.x > maxX) maxX = br.x;
        if (br.y > maxY) maxY = br.y;
    }

    const rectCenter = new Point2D([(minX + maxX) / 2, (minY + maxY) / 2]);

    let anchor = rectCenter;
    if (mousePosPix !== null) {
        const mouseReal = pageVS.viewport.unprojectPoint(mousePosPix);
        const combinedRect = Rectangle.fromPoints(new Point2D([minX, minY]), new Point2D([maxX, maxY]));
        if (combinedRect.contains(mouseReal)) {
            anchor = mouseReal;
        }
    }

    return anchor;
}
class PametCommands {
    @command('Create new note')
    createNewNote() {
        console.log('createNewNote command executed')

        // Get the real mouse pos on canvas (if it's over the viewport)
        let pageVS = getCurrentPageViewState();
        let mousePos = pamet.appViewState.mouseState.position
            ?? pamet.appViewState.mouseState.positionOnPress;
        let creationPos: Point2D;

        if (mousePos === null) {
            creationPos = pageVS.viewport.realCenter();
        } else {
            creationPos = pageVS.viewport.unprojectPoint(mousePos);
        }

        // Create a new note
        pageActions.startNoteCreation(pageVS, creationPos);
    }

    @command('Create Project Links Index')
    createProjectLinksIndex() {
        const pageVS = getCurrentPageViewState();
        try {
            pageActions.createProjectLinksIndex(pageVS);
        } catch (e) {
            log.error('Error creating project links index:', e);
        }
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
        let appViewState = pamet.appViewState;

        if (!appViewState.currentPageViewState) {
            // If last page - create default
            if (Array.from(pamet.pages()).length === 0) {
                let page = projectActions.createNewPageWithHelpNote();
                projectActions.setHomePage(appViewState, page.id);
                appActions.setCurrentPage(appViewState, page.id);
            } else {
                // It's a very niche case
                alert('Switching to the project root. You can create a new page then.');
                pamet.navigateTo(new PametRoute({
                    userId: pamet.appViewState.userId,
                    projectId: pamet.appViewState.currentProjectId ?? undefined,
                })).catch((e) => console.error('Error navigating to project root', e));
                return;
            }
        }

        // Determine forward link location - either under mouse or
        // in the center of the viewport
        // Get the real mouse pos on canvas (if it's over the viewport)
        let pageVS = getCurrentPageViewState();
        let mousePos = appViewState.mouseState.positionOnPress;
        let forwardLinkLocation: Point2D;
        if (mousePos === null) {
            forwardLinkLocation = pageVS.viewport.realCenter();
        } else {
            forwardLinkLocation = pageVS.viewport.unprojectPoint(mousePos);
        }

        projectActions.openPageCreationDialog(appViewState, forwardLinkLocation);
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

    @command('Undo')
    undo() {
        const pageVS = getCurrentPageViewState();
        pageActions.undoUserAction(pageVS);
    }

    @command('Redo')
    redo() {
        const pageVS = getCurrentPageViewState();
        pageActions.reduUserAction(pageVS);
    }

    @command('Page: Zoom in')
    pageZoomIn() {
        let pageVS = getCurrentPageViewState();
        pamet.pushNewViewportPosition(pageVS, pageVS.viewportCenter, pageVS.viewportHeight / 1.1);
    }

    @command('Page: Zoom out')
    pageZoomOut() {
        let pageVS = getCurrentPageViewState();
        pamet.pushNewViewportPosition(pageVS, pageVS.viewportCenter, pageVS.viewportHeight * 1.1);
    }

    @command('Page: Reset zoom')
    pageZoomReset() {
        let pageVS = getCurrentPageViewState();
        pamet.pushNewViewportPosition(pageVS, pageVS.viewportCenter, DEFAULT_VIEW_HEIGHT);
    }

    @command('Select all')
    selectAll() {
        let pageVS = getCurrentPageViewState();
        // Select all
        let selectionMap = new Map();
        for (let noteVS of pageVS.noteViewStatesById.values()) {
            selectionMap.set(noteVS, true);
        }
        for (let arrowVS of pageVS.arrowViewStatesById.values()) {
            selectionMap.set(arrowVS, true);
        }
        pageActions.updateSelection(pageVS, selectionMap);
    }

    @command('Copy selected elements')
    copySelectedElements() {
        const appViewState = pamet.appViewState;
        const pageVS = getCurrentPageViewState();

        // Collect selected notes
        const selectedNotes: Note[] = [];
        for (let elementVS of pageVS.selectedElementsVS.values()) {
            if (elementVS instanceof NoteViewState) {
                selectedNotes.push(elementVS.note());
            }
        }

        // Compute relativeTo via shared helper
        const relativeTo = computeSelectionAnchor(selectedNotes, appViewState.mouseState.positionOnPress, pageVS);

        pageActions.copySelectedElements(appViewState, pageVS, relativeTo);
    }

    @command('Cut')
    cutSelectedElements() {
        const appViewState = pamet.appViewState;
        const pageVS = getCurrentPageViewState();

        // Collect selected notes for anchor calculation
        const selectedNotes: Note[] = [];
        for (let elementVS of pageVS.selectedElementsVS.values()) {
            if (elementVS instanceof NoteViewState) {
                selectedNotes.push(elementVS.note());
            }
        }

        // Compute relativeTo via shared helper
        const relativeTo = computeSelectionAnchor(selectedNotes, appViewState.mouseState.position, pageVS);

        cutInternalProcedure(appViewState, pageVS, relativeTo).catch((error) => {
            log.error('Error in internal cut procedure:', error);
        });
    }

    @command('Open page properties')
    openPageProperties() {
        appActions.openPageProperties(pamet.appViewState);
    }

    @command('Delete current page')
    deleteCurrentPage() {
        const page = getCurrentPageViewState().page();
        if (confirmPageDeletion(page.name)) {
            projectActions.deletePageAndUpdateReferences(page);
        }
    }

    @command('Copy store state to clipboard')
    storeStateToClipboard() {
        storeStateToClipboard().catch(err => {
            log.error('Failed to store state to clipboard:', err);
        });
    }

    @command('Open projects dialog')
    deleteCurrentProject() {
        appActions.openProjectsDialog(pamet.appViewState);
    }

    @command('Create new project')
    createNewProject() {
        appActions.openCreateProjectDialog(pamet.appViewState);
    }

    @command('Paste')
    paste() {
        const appViewState = pamet.appViewState;
        const pageVS = getCurrentPageViewState();

        // Compute relative anchor for internal clipboard paste:
        // use mouse position if available, else viewport center.
        const mousePos = appViewState.mouseState.position;
        const relativeTo: Point2D = mousePos === null
            ? pageVS.viewport.realCenter()
            : pageVS.viewport.unprojectPoint(mousePos);

        pasteInternalProcedure(appViewState, pageVS, relativeTo).catch((error) => {
            log.error('Error in internal paste procedure:', error);
        });
    }

    @command('Paste special')
    pasteSpecial() {
        // Get the current page view state
        let pageVS = getCurrentPageViewState();

        // Get the mouse position or use viewport center
        let mousePos = pamet.appViewState.mouseState.position;
        let position: Point2D;

        if (mousePos === null) {
            position = pageVS.viewport.realCenter();
        } else {
            position = pageVS.viewport.unprojectPoint(mousePos);
        }

        // Get clipboard contents
        parseClipboardContents().then(clipboardContents => {
            // Pass the data to the action
            pasteSpecialProcedure(pageVS.page().id, position, clipboardContents).catch((error) => {
                log.error('Error in pasteSpecial procedure:', error);
            });

        }).catch((error) => {
            log.error('Error parsing clipboard contents:', error);
        });
    }

    @command('Open command palette')
    openCommandPalette() {
        appActions.openPageAndCommandPalette(pamet.appViewState, '>');
    }
    @command('Open page search')
    openPagePalette() {
        appActions.openPageAndCommandPalette(pamet.appViewState, '');
    }

    @command('Open project switch palette')
    openCommandPaletteWithProjectSwitch() {
        appActions.openProjectPalette(pamet.appViewState);
    }

    @command('Open local search')
    openLocalSearch() {
        appActions.openLocalSearch(pamet.appViewState);
    }

    @command('Open global search')
    openGlobalSearch() {
        appActions.openGlobalSearch(pamet.appViewState);
    }

    @command('Toggle last page')
    toggleLastPage() {
        log.info('Toggling last page');
        pamet.toggleLastPage();
    }

    @command('Refresh page')
    refresh() {
        window.location.reload();
    }
}

async function storeStateToClipboard() {
    // get the store state
    let fdsState = pamet.frontendDomainStore.data()
    // create a hash tree
    let hashTree = await buildHashTree(pamet.frontendDomainStore)
    // copy both to clipboard
    let nodes = Object.values(hashTree.nodes)
    let nodeData = nodes.map(node => node.data())
    let text = JSON.stringify({ fdsState, nodeData }, null, 2)
    try {
        await navigator.clipboard.writeText(text)
        log.info('Successfully copied to clipboard');
    } catch (err) {
        log.error('Failed to copy to clipboard:', err);
    }
}

export const commands = new PametCommands();
