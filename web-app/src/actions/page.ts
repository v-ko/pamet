import * as util from "../util";
import { PageMode, PageViewState, ViewportAutoNavAnimation } from "../components/page/PageViewState";
import { Point2D } from "../util/Point2D";

import { action } from "fusion/libs/Action";

import { getLogger } from "fusion/logging";
import { Rectangle } from "../util/Rectangle";
import { MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE } from "../core/constants";
import { EditComponentState } from "../components/note/EditComponent";
import { pamet } from "../core/facade";
import { Note } from "../model/Note";
import { TextNote } from "../model/TextNote";
import { minimalNonelidedSize } from "../components/note/util";
import { NoteViewState } from "../components/note/NoteViewState";
import { PametElement, PametElementData } from "../model/Element";
import { Arrow } from "../model/Arrow";

let log = getLogger('MapActions');

export const AUTO_NAVIGATE_TRANSITION_DURATION = 0.5; // seconds


class PageActions {

  @action
  updateGeometry(state: PageViewState, geometry: [number, number, number, number]) {
    state.viewportGeometry = geometry;
  }

  @action
  updateViewport(state: PageViewState, viewportCenter: Point2D, viewportHeight: number) {
    viewportHeight = Math.max(
      MIN_HEIGHT_SCALE,
      Math.min(viewportHeight, MAX_HEIGHT_SCALE))
    state.viewportCenter = viewportCenter
    state.viewportHeight = viewportHeight
  }

  // Don't include the mouse tracking with the user actions. We need it for
  // the commands though (e.g. creating a note via command)
  @action({ name: 'setRealMousePositionOnCanvas', issuer: 'PageView' })
  updateMousePosition(state: PageViewState, pixelSpaceMousePos: Point2D | null) {
    if (pixelSpaceMousePos === null) {
      state.realMousePositionOnCanvas = null;
      return;
    }
    let realMousePos = state.viewport.unprojectPoint(pixelSpaceMousePos);
    state.realMousePositionOnCanvas = realMousePos;
  }

  @action
  startDragNavigation(
    state: PageViewState,
    startPosition: Point2D) {

    state.setMode(PageMode.DragNavigation);
    state.dragNavigationStartPosition = startPosition;
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
    // let selectionMap: util.SelectionDict = new Map();
    // for (let noteVS of state.selectedElementsVS) {
    //   selectionMap.set(noteVS, false);
    // }
    // this.updateSelection(state, selectionMap);
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
        let newCenter = startCenter.add(
          endCenter.subtract(startCenter).multiply(timingFunction(t)));
        let newHeight = startHeight + (endHeight - startHeight) * timingFunction(t);
        pageActions.updateViewport(state, newCenter, newHeight);
        if (t === 1) {
          pageActions.endAutoNavigation(state);
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
    for (let noteVS of state.noteViewStatesByOwnId.values()) {
      let noteRect = noteVS.note().rect();
      if (unprojectedRect.intersects(noteRect)) {
        state.dragSelectedElementsVS.add(noteVS);
      }
    }

    // Get the arrows in the area
    for (let arrowVS of state.arrowViewStatesByOwnId.values()) {
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
    let note = TextNote.createNew(state.page.id);
    let noteRect = note.rect()
    noteRect.setTopLeft(realPosition)
    note.setRect(noteRect)

    let editWindowState = new EditComponentState(pixSpacePosition, note);
    state.noteEditWindowState = editWindowState;
  }

  @action
  startEditingNote(state: PageViewState, note: Note) {
    let spawnPos = state.viewport.projectPoint(note.rect().topLeft());
    let editWindowState = new EditComponentState(spawnPos, note);
    state.noteEditWindowState = editWindowState;
  }

  @action
  saveEditedNote(state: PageViewState, note: Note) {
    let editWS = state.noteEditWindowState;

    if (editWS === null) {
      throw Error('saveEditedNote called without noteEditWindowState')
    }

    // If creating
    if (editWS.creatingNote) {
      let newNote = note;
      // Autosize the note
      let minimalSize = minimalNonelidedSize(newNote);
      let rect = newNote.rect();
      rect.setSize(util.snapVectorToGrid(minimalSize));
      rect.setTopLeft(util.snapVectorToGrid(rect.topLeft()));
      newNote.setRect(rect);
      pamet.insertNote(newNote);

    } else { // If editing
      let editedNote = note;
      pamet.updateNote(editedNote);
    }
    state.noteEditWindowState = null;
  }

  @action
  abortEditingNote(state: PageViewState) {
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
      let newSize = util.snapVectorToGrid(minimalSize)

      if (rect.size().equals(newSize)) {  // Skip if the size is the same
        continue;
      }
      rect.setSize(newSize);
      note.setRect(rect);
      pamet.updateNote(note);
    }
  }

  @action
  deleteElements(elements: PametElement<PametElementData>[]) {
    // Split into notes and arrows and where a note has connected arrows -
    // add them for removal too
    let notesForRemoval: Note[] = [];
    let arrowsForRemoval: Arrow[] = [];
    let noteIds = new Set<string>(); // For checking if the note has a connected arrow

    for (let element of elements) {
      if (element instanceof Note) {
        notesForRemoval.push(element)
      } else if (element instanceof Arrow) {
        arrowsForRemoval.push(element)
      }
    }

    // Get the page id (should be the same for all notes)
    let pageId = notesForRemoval[0].parentId;
    let isSame = notesForRemoval.every((note) => note.parentId === pageId);
    if (!isSame) {
      throw Error('Trying to delete notes from different pages')
    }

    // Get the arrows that are connected to the notes (check just one page)
    let allArrows = pamet.arrows({parentId: pageId});
    for (let arrow of allArrows) {
      // If the arrow has tail/head in the notesForRemoval - add it of removal
      if (arrow.tail_note_id && noteIds.has(arrow.tail_note_id) ||
        arrow.head_note_id && noteIds.has(arrow.head_note_id)) {
        arrowsForRemoval.push(arrow);
      }
    }

    // Remove the elements
    for (let note of notesForRemoval) {
      pamet.removeNote(note);
    }
    for (let arrow of arrowsForRemoval) {
      pamet.removeArrow(arrow);
    }
  }

  @action
  deleteSelectedElements(state: PageViewState){
    let elements = Array.from(state.selectedElementsVS).map((elementVS) => elementVS.element());
    this.deleteElements(elements);
    this.clearSelection(state);
  }
}

export const pageActions = new PageActions();
