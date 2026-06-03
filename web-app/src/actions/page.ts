import * as util from "@/app/util";
import { PageMode, PageViewState, ViewportAutoNavAnimation } from "@/views/page/PageViewState";
import { Point2D } from "sivkit/primitives/Point2D";
import { pamet } from "@/app/facade";

import { action } from "sivkit/registries/Action";

import { getLogger } from "sivkit/logging";
import { Rectangle } from "sivkit/primitives/Rectangle";
import { Size } from "sivkit/primitives/Size";
import { AGU, MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE, MIN_NOTE_HEIGHT } from "@/app/constants";
import { Note } from "@/model/Note";
import { minimalNonelidedSize } from "@/views/note/note-dependent-utils";
import { NoteViewState } from "@/views/note/NoteViewState";
import { Arrow } from "@/model/Arrow";
import { ArrowViewState } from "@/views/arrow/ArrowViewState";
import { NoteEditViewState } from "@/views/note/NoteEditViewState";
import { CardNote } from "@/model/CardNote";
import { linkUpdatesForPageRename } from '@/model/correctness';
import { UNDO_ACTION_NAME, REDO_ACTION_NAME } from "@/services/undo/UndoService";
import { PametRoute } from "@/services/routing/PametRoute";
import { AppViewState } from "@/views/AppViewState";
import { Page } from "@/model/Page";


let log = getLogger('MapActions');

export const AUTO_NAVIGATE_TRANSITION_DURATION = 0.5; // seconds


class PageActions {

  @action
  updateGeometry(state: PageViewState, geometry: [number, number, number, number]) {
    state.viewportGeometry = geometry;
  }

  @action
  updateResizeCircleOutline(state: PageViewState, noteVS: NoteViewState | null) {
    state.hoveredResizeNoteVS = noteVS;
  }

  @action({ issuer: 'user' })
  createProjectLinksIndex(state: PageViewState) {
    const pageId = state.page().id;
    const center = state.viewport.realCenter();

    // Create header note
    const header = CardNote.createNew({ pageId });
    header.content.text = 'Project links index (double-click to generate missing links, for e.g. new pages)';
    header.metadata.is_project_index_header = true;
    // Use surface styling for the header
    header.style.color_role = 'onSurface';
    header.style.background_color_role = 'neutral';

    // Auto-size and center
    const rect = header.rect();
    const size = util.snapVectorToGrid(minimalNonelidedSize(header));
    rect.setSize(size);
    rect.moveCenter(center);
    // Snap final position to grid
    rect.setTopLeft(util.snapVectorToGrid(rect.topLeft()));
    header.setRect(rect);

    pamet.insertNote(header);

    // Generate all missing links under the header (no alert here)
    this.generateProjectIndexMissingLinks(state, header);
  }

  @action({ issuer: 'user' })
  generateProjectIndexMissingLinks(state: PageViewState, header: Note): number {
    const pageId = state.page().id;

    // Collect all pages in store iteration order
    const allPages = Array.from(pamet.pages());

    // Represented page ids on current page
    const represented = new Set<string>();
    for (const note of pamet.notes({ parentId: pageId })) {
      if (note instanceof CardNote && note.content.page_ref) {
        represented.add(note.content.page_ref.id);
      }
    }

    // Missing pages (include current page if not present)
    const missingPages = allPages.filter(p => !represented.has(p.id));
    if (missingPages.length === 0) return 0;

    const headerRect = header.rect();
    const itemLeft = headerRect.left() + AGU; // 1 AGU inset
    const itemWidth = Math.max(AGU, headerRect.width - 2 * AGU); // fixed width under header
    const itemHeight = MIN_NOTE_HEIGHT; // standard two-row height (3*AGU)

    // Existing notes on page used for collision checks (notes only; arrows not blockers)
    const existingNotes: Note[] = Array.from(pamet.notes({ parentId: pageId }));

    let created = 0;
    for (const p of missingPages) {
      const link = CardNote.createInternalLinkNote(p, pageId);

      // Seek a free slot scanning downward
      let currentTop = headerRect.bottom() + AGU; // first row under header
      while (true) {
        const candidate = new Rectangle([itemLeft, currentTop, itemWidth, itemHeight]);
        let collided = false;
        for (const n of existingNotes) {
          // Skip the header itself
          if (n.id === header.id) continue;
          const nr = n.rect();
          if (candidate.intersects(nr)) {
            currentTop = nr.bottom() + AGU;
            collided = true;
            break;
          }
        }
        if (!collided) {
          const rect = link.rect();
          rect.setTopLeft(util.snapVectorToGrid(new Point2D([candidate.left(), candidate.top()])));
          rect.setSize(new Size([itemWidth, itemHeight]));
          link.setRect(rect);
          break;
        }
      }

      pamet.insertNote(link);
      existingNotes.push(link);
      created += 1;
    }

    return created;
  }

  @action
  updateViewport(state: PageViewState, viewportCenter: Point2D, viewportHeight: number) {
    viewportHeight = Math.max(
      MIN_HEIGHT_SCALE,
      Math.min(viewportHeight, MAX_HEIGHT_SCALE))
    state.viewportCenter = viewportCenter
    state.viewportHeight = viewportHeight
  }

  @action
  startDragNavigation(
    state: PageViewState) {

    state.setMode(PageMode.DragNavigation);
    state.viewportCenterOnModeStart = state.viewportCenter;
  }

  @action
  dragNavigationMove(state: PageViewState, delta: Point2D) {
    let deltaUnprojected = delta.divide(state.viewport.heightScaleFactor());
    state.viewportCenter = state.viewportCenterOnModeStart.add(deltaUnprojected);
  }

  @action
  endDragNavigation(state: PageViewState) {
    state.setMode(PageMode.None);
    // Sync viewport to live page after panning in history overlay
    if (state.isReplay && pamet.appViewState.currentPageViewState) {
      this.updateViewport(
        pamet.appViewState.currentPageViewState,
        state.viewportCenter,
        state.viewportHeight,
      );
    }
    const route = pamet.appViewState.toRoute();
    pamet.router.replaceRoute(route);
  }

  @action
  updateSelection(state: PageViewState, selectionMap: util.SelectionDict) {
    // Add all keys that are true to the selection
    for (let [pageChild, selected] of selectionMap) {
      // let selected = selectionMap.get(pageChild);
      if (selected === true) { // && !state.selectedChildren.has(pageChild)
        state.selectedElementsVS.add(pageChild);
      } else {
        state.selectedElementsVS.delete(pageChild);
      }
    }
  }

  @action
  clearSelection(state: PageViewState) {
    state.selectedElementsVS.clear();
  }

  @action
  startAutoNavigation(
    state: PageViewState,
    viewportCenter: Point2D,
    viewportHeight: number) {

    state.mode = PageMode.AutoNavigation;
    let animation: ViewportAutoNavAnimation = {
      startCenter: state.viewportCenter,
      endCenter: viewportCenter,
      startHeight: state.viewportHeight,
      endHeight: viewportHeight,
      startTime: Date.now(),
      duration: AUTO_NAVIGATE_TRANSITION_DURATION * 1000,
      timingFunctionName: 'linear',
    };
    state.autoNavAnimation = animation;
  }

  @action
  updateAutoNavigation(state: PageViewState) {
    if (state.autoNavAnimation) {
      let animation = state.autoNavAnimation;
      if (animation) {
        let startCenter = animation.startCenter;
        let endCenter = animation.endCenter;
        let startHeight = animation.startHeight;
        let endHeight = animation.endHeight;
        let duration = animation.duration;
        let startTime = animation.startTime;
        let timingFunctionName = animation.timingFunctionName;
        let timingFunction;
        if (timingFunctionName === 'linear') {
          timingFunction = (t: any) => {
            return t;
          }
        } else {
          throw Error('Timing function not implemented')
        }
        let currentTime = Date.now();
        let t = (currentTime - startTime) / duration;
        if (t > 1) {
          t = 1;
        }
        let newCenter = endCenter.copy();
        newCenter.subtract_inplace(startCenter);
        newCenter.multiply_inplace(timingFunction(t));
        newCenter.add_inplace(startCenter);

        let newHeight = startHeight + (endHeight - startHeight) * timingFunction(t);
        this.updateViewport(state, newCenter, newHeight);
        if (t === 1) {
          this.endAutoNavigation(state);
        }
        let lastUpdateTime = Date.now();
        // console.log('lastUpdateTime', lastUpdateTime)
        animation.lastUpdateTime = lastUpdateTime;
        state.autoNavAnimation = animation;
      }
    }
  }

  @action
  endAutoNavigation(state: PageViewState) {
    if (state.autoNavAnimation) {
      state.viewportCenter = state.autoNavAnimation.endCenter;
      state.viewportHeight = state.autoNavAnimation.endHeight;
      state.autoNavAnimation = null;
    }
    state.mode = PageMode.None;
  }

  @action
  startDragSelection(state: PageViewState, startPosition: Point2D) {
    state.mode = PageMode.DragSelection;
    state.mousePositionOnDragSelectionStart = startPosition;
  }

  @action
  updateDragSelection(state: PageViewState, pointerPosition: Point2D) {
    if (state.mousePositionOnDragSelectionStart === null) {
      log.error('updateDragSelection called without mousePositionOnDragSelectionStart');
      return;
    }
    // console.log('updateDragSelection', state.mousePositionOnDragSelectionStart, pointerPosition);
    let selectionRectangle = Rectangle.fromPoints(state.mousePositionOnDragSelectionStart, pointerPosition);
    let unprojectedRect = state.viewport.unprojectRect(selectionRectangle);

    state.dragSelectionRectData = selectionRectangle.data();
    state.dragSelectedElementsVS.clear();

    // Get notes in the area
    for (let noteVS of state.noteViewStatesById.values()) {
      let noteRect = new Rectangle(noteVS._elementData.geometry);
      if (unprojectedRect.intersects(noteRect)) {
        state.dragSelectedElementsVS.add(noteVS);
      }
    }

    // Get the arrows in the area
    for (let arrowVS of state.arrowViewStatesById.values()) {
      if (arrowVS.intersectsRect(unprojectedRect)) {
        state.dragSelectedElementsVS.add(arrowVS);
      }
    }
  }

  @action
  endDragSelection(state: PageViewState) {
    // Add dragSelectedChildren to selectedChildren
    for (let child of state.dragSelectedElementsVS) {
      state.selectedElementsVS.add(child);
    }
    state.clearMode();
  }

  @action
  startNoteCreation(state: PageViewState, realPosition: Point2D) {
    let pixSpacePosition = state.viewport.projectPoint(realPosition);
    let note = CardNote.createNew({ pageId: state.page().id });
    let noteRect = note.rect()
    noteRect.setTopLeft(realPosition)
    note.setRect(noteRect)

    let editWindowState = new NoteEditViewState(pixSpacePosition, note);
    state.noteEditWindowState = editWindowState;
  }

  @action
  startEditingNote(state: PageViewState, note: Note) {
    // Block editing for project index header notes and explain behavior
    if (note.metadata?.is_project_index_header) {
      window.alert('Project Links Index is not editable. Double-click it to generate or update links under it.');
      return;
    }
    let spawnPos = state.viewport.projectPoint(note.rect().topLeft());
    let editWindowState = new NoteEditViewState(spawnPos, note);
    state.noteEditWindowState = editWindowState;
  }

  @action
  saveEditedNote(state: PageViewState, note: Note) {
    const editWS = state.noteEditWindowState;
    if (!editWS) {
      throw new Error('saveEditedNote called without noteEditWindowState');
    }

    const projectId = pamet.appViewState.currentProjectId;
    if (!projectId) {
      throw new Error('No project loaded');
    }

    // Save the note
    if (editWS.creatingNote) {
      const minimalSize = minimalNonelidedSize(note);
      const rect = note.rect();
      let snappedSize = util.snapVectorToGrid(minimalSize);
      rect.setSize(snappedSize);
      let snappedTopLeft = util.snapVectorToGrid(rect.topLeft())
      rect.setTopLeft(snappedTopLeft);
      note.setRect(rect);
      pamet.insertNote(note);
    } else {
      pamet.updateNote(note);
    }

    // Register file URL for the image if present
    if (note.content.image?.path) {
      state.addUrlForFilePath(note.content.image.path);
    }

    state.noteEditWindowState = null;
  }

  @action
  closeNoteEditWindow(state: PageViewState) {
    state.noteEditWindowState = null;
  }

  @action
  startEditWindowDrag(state: PageViewState, clickPos: Point2D) {
    state.setMode(PageMode.DraggingEditWindow);
    let editWS = state.noteEditWindowState!;
    if (editWS === null) {
      log.error('startEditWindowDrag called without noteEditWindowState');
      return;
    }

    editWS.isBeingDragged = true;
    editWS.dragStartClickPos = clickPos;
    editWS.topLeftOnDragStart = editWS.center;
  }

  @action
  updateEditWindowDrag(state: PageViewState, mousePos: Point2D) {
    let editWS = state.noteEditWindowState!;
    if (editWS === null) {
      log.error('updateEditWindowDrag called without noteEditWindowState');
      return;
    }
    let delta = mousePos.subtract(editWS.dragStartClickPos);
    editWS.center = editWS.topLeftOnDragStart.add(delta);
  }

  @action
  endEditWindowDrag(state: PageViewState) {
    state.clearMode();
  }

  @action
  clearMode(state: PageViewState) {
    state.clearMode();
  }

  @action
  autoSizeSelectedNotes(state: PageViewState) {
    for (let elementVS of state.selectedElementsVS) {
      if (!(elementVS instanceof NoteViewState)) { // Skip arrows
        continue;
      }
      let noteVS = elementVS as NoteViewState;
      let note = noteVS.note();
      let minimalSize = minimalNonelidedSize(note);
      let rect = note.rect();
      util.snapVectorToGrid_inplace(minimalSize)

      if (rect.size().equals(minimalSize)) {  // Skip if the size is the same
        continue;
      }
      rect.setSize(minimalSize);
      note.setRect(rect);
      pamet.updateNote(note);
    }
  }

  @action
  deleteSelectedElements(state: PageViewState) {
    let elements = Array.from(state.selectedElementsVS).map((elementVS) => elementVS.element());
    if (elements.length === 0) {
      log.warning('deleteSelectedElements called with no selected elements');
      return;
    }

    // Split selected elements into notes and arrows
    let notesForRemoval = new Map<string, Note>();
    let arrowsForRemoval = new Map<string, Arrow>();
    let pageId: string = elements[0].parentId;

    for (let element of elements) {
      if (element.parentId !== pageId) {
        throw Error('Trying to delete elements from different pages')
      }
      if (element instanceof Note) {
        notesForRemoval.set(element.id, element)
      } else if (element instanceof Arrow) {
        arrowsForRemoval.set(element.id, element)
      }
    }

    // Also remove arrows connected to deleted notes
    for (let arrow of pamet.arrows({ parentId: pageId })) {
      if (arrow.tailNoteId && notesForRemoval.has(arrow.tailNoteId) ||
        arrow.headNoteId && notesForRemoval.has(arrow.headNoteId)) {
        arrowsForRemoval.set(arrow.id, arrow);
      }
    }

    for (let note of notesForRemoval.values()) {
      pamet.removeNote(note);
    }
    for (let arrow of arrowsForRemoval.values()) {
      pamet.removeArrow(arrow);
    }

    // Files are NOT removed when notes are deleted — orphan cleanup is handled separately.
    this.clearSelection(state);
  }

  @action
  colorSelectedElements(state: PageViewState, colorRole: string | null, backgroundColorRole: string | null, arrowColorRole: string | null) {
    for (let elementVS of state.selectedElementsVS) {
      if (elementVS instanceof NoteViewState) {
        let note = elementVS.note();
        if (colorRole !== null) {
          note.style.color_role = colorRole;
        }
        if (backgroundColorRole !== null) {
          note.style.background_color_role = backgroundColorRole;
        }
        pamet.updateNote(note);
      } else if (elementVS instanceof ArrowViewState && arrowColorRole !== null) {
        let arrow = elementVS.arrow();
        arrow.colorRole = arrowColorRole;
        pamet.updateArrow(arrow);
      }
    }
    this.clearSelection(state);
  }

  @action
  updatePageProperties(newPageState: Page) {
    // Detect name change to update internal link texts across project
    const current = pamet.page(newPageState.id);
    const oldName = current?.name;
    const newName = newPageState.name;

    pamet.updatePage(newPageState);

    if (oldName !== undefined && oldName !== newName) {
      const updates = linkUpdatesForPageRename(
        pamet.currentProjectStore, newPageState.id, newName, newPageState.path
      );
      for (const u of updates) {
        pamet.updateNote(u.updated);
      }
    }
  }

  @action({ issuer: 'paste-special-procedure' })
  pasteSpecialAddElements(notes: Note[]) {
    // Add new notes via facade
    for (let note of notes) {
      pamet.insertNote(note);
    }
  }

  @action({ issuer: 'user' })
  pasteInternalAddElements(
    appViewState: AppViewState,
    state: PageViewState,
    notes: Note[],
    arrows: Arrow[]) {

    for (let note of notes) {
      pamet.insertNote(note);
    }
    for (let arrow of arrows) {
      pamet.insertArrow(arrow);
    }
    log.info('Pasted', notes.length, 'notes,', arrows.length, 'arrows');
    // Clear selection
    this.clearSelection(state);
  }

  @action({ issuer: 'user' })
  cutRemoveElements(
    appViewState: AppViewState,
    state: PageViewState,
    notes: Note[],
    arrows: Arrow[]
  ) {
    // Remove arrows
    for (let arrow of arrows) {
      pamet.removeArrow(arrow);
    }
    // Remove notes
    for (let note of notes) {
      pamet.removeNote(note);
    }
    // Files are NOT removed on cut; the clipboard keeps references for paste.

    // Clear selection after cut
    this.clearSelection(state);
    log.info(`Cut removed ${notes.length} notes, ${arrows.length} arrows`);
  }

  @action({ issuer: 'service', name: UNDO_ACTION_NAME })
  undoUserAction(state: PageViewState) {
    pamet.undoService.undo(state._pageData.id);
  }

  @action({ issuer: 'service', name: REDO_ACTION_NAME })
  reduUserAction(state: PageViewState) {
    pamet.undoService.redo(state._pageData.id);
  }

  @action
  copySelectedElements(appViewState: AppViewState, state: PageViewState, relativeTo: Point2D) {
    // Gather selected notes
    const selectedNotes: Note[] = [];
    const selectedNoteIds = new Set<string>();

    for (const elementVS of state.selectedElementsVS) {
      if (elementVS instanceof NoteViewState) {
        const note = elementVS.note();
        selectedNotes.push(note);
        selectedNoteIds.add(note.id);
      }
    }

    if (selectedNotes.length === 0) {
      log.warning('copySelectedElements called with no selected notes');
      pamet.setClipboard([], null);
      return;
    }

    const clipboardEntities: (Note | Arrow)[] = [];

    // Clone and transform notes to relative coordinates
    for (const note of selectedNotes) {
      const cloned = note.copy() as Note;
      const rect = cloned.rect();
      rect.setTopLeft(rect.topLeft().subtract(relativeTo));
      cloned.setRect(rect);
      clipboardEntities.push(cloned);
    }

    // Include eligible arrows from the current page
    for (const arrow of pamet.arrows({ parentId: state.page().id })) {
      // If anchored, both endpoints must be within selected notes; otherwise skip
      if (arrow.headNoteId && !selectedNoteIds.has(arrow.headNoteId)) {
        continue;
      }
      if (arrow.tailNoteId && !selectedNoteIds.has(arrow.tailNoteId)) {
        continue;
      }

      const cloned = arrow.copy() as Arrow;

      // Adjust absolute endpoints relative to anchor
      if (cloned.headPositionIsAbsolute && cloned.headPoint) {
        cloned.headPoint = cloned.headPoint.subtract(relativeTo);
      }
      if (cloned.tailPositionIsAbsolute && cloned.tailPoint) {
        cloned.tailPoint = cloned.tailPoint.subtract(relativeTo);
      }

      // Adjust midpoints
      const mids = cloned.midPoints().map(p => p.subtract(relativeTo));
      cloned.replaceMidpoints(mids);

      clipboardEntities.push(cloned);
    }

    pamet.setClipboard(clipboardEntities, appViewState.currentProjectId);
    log.info('Copied to internal clipboard', clipboardEntities.length, 'entities');
  }

  /**
   * Open the link target of a note in a new browser tab.
   * Returns the URL that was opened, or null if the note has no link.
   */
  openNoteLinkInNewTab(noteVS: NoteViewState, userId: string, projectId: string | undefined): string | null {
    let note = noteVS.note();
    if (note instanceof CardNote && note.content.page_ref) {
      let targetPage = pamet.page(note.content.page_ref.id);
      if (targetPage !== undefined) {
        let route = new PametRoute({
          userId,
          projectId,
          pageId: targetPage.id,
        });
        let url = route.toRelativeReference();
        window.open(url, '_blank');
        return url;
      }
    }
    if (note instanceof CardNote && note.hasExternalLink) {
      let url = note.content.url;
      if (!url?.startsWith('http://') && !url?.startsWith('https://')) {
        url = '//' + url;
      }
      window.open(url!, '_blank');
      return url!;
    }
    return null;
  }

  @action
  setClipboardPreview(state: PageViewState, show: boolean) {
    state.showClipboardPreview = show;
  }

}

export const pageActions = new PageActions();
