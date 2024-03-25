import { SelectionDict as SelectionMap } from "../util";
import { PageMode, PageViewState, ViewportAutoNavAnimation } from "../components/canvas/PageViewState";
import { Point2D } from "../util/Point2D";

import { makeObservable } from "mobx";
import { action } from "mobx"

import { getLogger } from "../fusion/logging";
import { Rectangle } from "../util/Rectangle";
import { MAX_HEIGHT_SCALE, MIN_HEIGHT_SCALE } from "../constants";
// import { action } from "../fusion/libs/Action";

let log = getLogger('MapActions');

export const AUTO_NAVIGATE_TRANSITION_DURATION = 0.5; // seconds


class MapActions {
  constructor() {
    makeObservable(this);
  }

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

    if (state.viewportCenterOnModeStart === null) {
      log.error('dragNavigationMove called without viewportCenterOnModeStart');
      return;
    }

    let deltaUnprojected = delta.divide(state.viewport.heightScaleFactor());
    state.viewportCenter = state.viewportCenterOnModeStart.add(deltaUnprojected);
  }

  @action
  endDragNavigation(state: PageViewState) {
    state.setMode(PageMode.None);
  }

  @action
  updateSelection(state: PageViewState, selectionMap: SelectionMap) {
    console.log('[updateSelection]', state, selectionMap);
    // Add all keys that are true to the selection
    for (let [pageChild, selected] of selectionMap) {
      // let selected = selectionMap.get(pageChild);
      if (selected === true) { // && !state.selectedChildren.has(pageChild)
        state.selectedChildren.add(pageChild);
      } else {
        state.selectedChildren.delete(pageChild);
      }
    }
  };

  @action
  clearSelection(state: PageViewState) {
    console.log('[clearSelection]');
    let selectionMap: SelectionMap = new Map();
    for (let noteVS of state.selectedChildren) {
      selectionMap.set(noteVS, false);
    }
    this.updateSelection(state, selectionMap);
  };

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
  };

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
          timingFunction = (t) => {
            return t;
          }
        }
        let currentTime = Date.now();
        let t = (currentTime - startTime) / duration;
        if (t > 1) {
          t = 1;
        }
        let newCenter = startCenter.add(
          endCenter.subtract(startCenter).multiply(timingFunction(t)));
        let newHeight = startHeight + (endHeight - startHeight) * timingFunction(t);
        mapActions.updateViewport(state, newCenter, newHeight);
        if (t === 1) {
          mapActions.endAutoNavigation(state);
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
    state.dragSelectedChildren.clear();



    // Get notes in the area
    for (let noteVS of state.noteViewStatesByOwnId.values()) {
      let noteRect = noteVS.note.rect();
      if (unprojectedRect.intersects(noteRect)) {
        state.dragSelectedChildren.add(noteVS);
      }
    }

    // Get the arrows in the area
    for (let arrowVS of state.arrowViewStatesByOwnId.values()) {
      if (arrowVS.intersectsRect(unprojectedRect)) {
        state.dragSelectedChildren.add(arrowVS);
      }
    }
  }

  @action
  endDragSelection(state: PageViewState) {
    // Add dragSelectedChildren to selectedChildren
    for (let child of state.dragSelectedChildren) {
      state.selectedChildren.add(child);
    }
    state.clearMode();
  }
}

export const mapActions = new MapActions();
