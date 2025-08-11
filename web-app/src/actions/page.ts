import * as util from "@/util";
import { PageMode, PageViewState, ViewportAutoNavAnimation } from "@/components/page/PageViewState";
import { Point2D } from "fusion/primitives/Point2D";

import { action } from "fusion/libs/Action";

import { getLogger } from "fusion/logging";
import { Rectangle } from "fusion/primitives/Rectangle";
import { MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE } from "@/core/constants";
import { pamet } from "@/core/facade";
import { Note } from "@/model/Note";
import { TextNote } from "@/model/TextNote";
import { minimalNonelidedSize } from "@/components/note/note-dependent-utils";
import { NoteViewState } from "@/components/note/NoteViewState";
import { PametElement, PametElementData } from "@/model/Element";
import { Arrow } from "@/model/Arrow";
import { ArrowViewState } from "@/components/arrow/ArrowViewState";
import { Page } from "@/model/Page";
import { MediaItem } from "fusion/libs/MediaItem";
import { ImageNote } from "@/model/ImageNote";
import { NoteEditViewState } from "@/components/note/NoteEditViewState";

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
  @action({ name: 'updateProjectedMousePosition', issuer: 'PageView' })
  updateMousePosition(state: PageViewState, pixelSpaceMousePos: Point2D | null) {
    if (pixelSpaceMousePos === null) {
      state.projectedMousePosition = null;
      return;
    }
    state.projectedMousePosition = pixelSpaceMousePos;
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
    for (let noteVS of state.noteViewStatesByOwnId.values()) {
      let noteRect = new Rectangle(noteVS._noteData.geometry);
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

    let editWindowState = new NoteEditViewState(pixSpacePosition, note);
    state.noteEditWindowState = editWindowState;
  }

  @action
  startEditingNote(state: PageViewState, note: Note) {
    let spawnPos = state.viewport.projectPoint(note.rect().topLeft());
    let editWindowState = new NoteEditViewState(spawnPos, note);
    state.noteEditWindowState = editWindowState;
  }

  @action
  saveEditedNote(state: PageViewState, note: Note, addedMediaItem: MediaItem | null, removedMediaItem: MediaItem | null) {
    const editWS = state.noteEditWindowState;
    if (!editWS) {
      throw new Error('saveEditedNote called without noteEditWindowState');
    }

    const projectId = pamet.appViewState.currentProjectId;
    if (!projectId) {
      throw new Error('No project loaded');
    }

    // Handle media item changes
    if (addedMediaItem) {
      pamet.insertOne(addedMediaItem);
    }

    if (removedMediaItem) {
      if (!addedMediaItem) {
        throw new Error('Removed media item without added media item');
      }
      pamet.moveMediaToTrash(removedMediaItem).catch(
        err => log.error('Failed to move media to trash:', err));
      pamet.removeOne(removedMediaItem);
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
  deleteElements(elements: PametElement<PametElementData>[]) {
    // Split into notes and arrows and where a note has connected arrows -
    // add them for removal too
    let notesForRemoval: Note[] = [];
    let arrowsForRemoval: Arrow[] = [];
    let mediaItemsForTrashing: MediaItem[] = [];
    let noteIds = new Set<string>(); // For checking if the note has a connected arrow
    let pageId: string = elements[0].parentId;

    for (let element of elements) {
      if (element instanceof Note) {
        notesForRemoval.push(element)
        noteIds.add(element.own_id)

        // Mark media for trashing if the note has an image
        if (element instanceof ImageNote) {  // Should catch both card notes and image notes
          let mediaItem = pamet.mediaItem(element.content.image_id!);
          if (mediaItem) {
            mediaItemsForTrashing.push(mediaItem);
          } else {
            log.warning(`ImageNote with id ${element.id} has no media item associated.`);
          }
        }
      } else if (element instanceof Arrow) {
        arrowsForRemoval.push(element)
      }

      // Verify pageId
      if (element.parentId !== pageId) {
        throw Error('Trying to delete elements from different pages')
      }
    }

    // Get the arrows that are connected to the notes (check just one page)
    let allArrows = pamet.arrows({ parentId: pageId });
    for (let arrow of allArrows) {
      // If the arrow has tail/head in the notesForRemoval - add it of removal
      if (arrow.tailNoteId && noteIds.has(arrow.tailNoteId) ||
        arrow.headNoteId && noteIds.has(arrow.headNoteId)) {
        arrowsForRemoval.push(arrow);
      }
    }

    // Remove the notes
    for (let note of notesForRemoval) {
      pamet.removeNote(note);
    }

    // Remove the arrows
    for (let arrow of arrowsForRemoval) {
      pamet.removeArrow(arrow);
    }

    // Trash media items
    for (let mediaItem of mediaItemsForTrashing) {
      pamet.moveMediaToTrash(mediaItem).catch(
        err => log.error('Failed to move media to trash:', err));
      pamet.removeOne(mediaItem);
    }
  }

  @action
  deleteSelectedElements(state: PageViewState) {
    let elements = Array.from(state.selectedElementsVS).map((elementVS) => elementVS.element());
    this.deleteElements(elements);
    this.clearSelection(state);
  }

  @action
  colorSelectedNotes(state: PageViewState, colorRole: string | null, backgroundColorRole: string | null) {
    for (let elementVS of state.selectedElementsVS) {
      if (!(elementVS instanceof NoteViewState)) { // Skip arrows
        continue;
      }
      let noteVS = elementVS as NoteViewState;
      let note = noteVS.note();
      if (colorRole !== null) {
        note.style.color_role = colorRole;
      }
      if (backgroundColorRole !== null) {
        note.style.background_color_role = backgroundColorRole;
      }
      pamet.updateNote(note);
    }
  }

  @action
  colorSelectedArrows(state: PageViewState, colorRole: string) {
    for (let elementVS of state.selectedElementsVS) {
      if (!(elementVS instanceof ArrowViewState)) { // Skip notes
        continue;
      }
      let arrowVS = elementVS as ArrowViewState;
      let arrow = arrowVS.arrow();
      arrow.colorRole = colorRole;
      pamet.updateArrow(arrow);
    }
  }

  @action
  updatePageProperties(newPageState: Page) {
    pamet.updatePage(newPageState);
  }

  @action({ issuer: 'paste-special-procedure' })
  pasteSpecialAddElements(notes: Note[], mediaItems: MediaItem[]) {
    // Add new media items via facade
    for (let mediaItem of mediaItems) {
      pamet.insertOne(mediaItem);
    }

    // Add new notes via facade
    for (let note of notes) {
      pamet.insertNote(note);
    }
  }
}

export const pageActions = new PageActions();
