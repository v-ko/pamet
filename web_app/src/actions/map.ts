import { SelectionDict } from "../util";
import { action, makeObservable } from "mobx";
import { MapPageMode, MapPageViewState, ViewportAutoNavAnimation } from "../components/MapPage/MapPageViewState";
import { Point2D } from "../util/Point2D";


export const AUTO_NAVIGATE_TRANSITION_DURATION = 0.5; // seconds


class MapActions {
  constructor() {
    makeObservable(this);
  }

  @action
  updateGeometry(state: MapPageViewState, geometry: [number, number, number, number]) {
    state.geometry = geometry;
  }

  @action
  updateViewport(
    state: MapPageViewState,
    viewportCenter: Point2D,
    viewportHeight: number) {

    state.viewportCenter = viewportCenter
    state.viewportHeight = viewportHeight
  }

  @action
  startDragNavigation(
    state: MapPageViewState,
    startPosition: Point2D) {

    state.set_mode(MapPageMode.DragNavigation);
    state.dragNavigationStartPosition = startPosition;
    state.viewportCenterOnModeStart = state.viewportCenter;
  }

  @action
  dragNavigationMove(
    state: MapPageViewState,
    delta: Point2D) {

    let delta_unproj = delta.divide(state.viewport.heightScaleFactor());
    let new_center = state.viewportCenterOnModeStart?.add(delta_unproj) as Point2D;
    state.viewportCenter = new_center;
  }

  @action
  endDragNavigation(state: MapPageViewState) {
    state.set_mode(MapPageMode.None);
  }

  @action
  updateSelection = (state: MapPageViewState, selectionDict: SelectionDict) => {
    // Add all keys that are true to the selection
    let newSelection: Array<string> = state.selection;
    for (let key in selectionDict) {
      if (selectionDict[key] && !state.selection.includes(key)) {
        newSelection.push(key);
      }
    }
    // Remove all keys that are false from the selection
    newSelection = newSelection.filter((key) => selectionDict[key] !== false);
    state.selection = newSelection;
  };

  @action
  clearSelection = (state: MapPageViewState) => {
    let selectionDict: SelectionDict = {};
    for (let noteId of state.selection) {
      selectionDict[noteId] = false;
    }
    this.updateSelection(state, selectionDict);
  };

  @action
  startAutoNavigation = (
    state: MapPageViewState,
    viewportCenter: Point2D,
    viewportHeight: number) => {

    state.mode = MapPageMode.AutoNavigation;
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
  updateAutoNavigation = (state: MapPageViewState) => {
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
          mapActions.finishAutoNavigation(state);
        }
        let lastUpdateTime = Date.now();
        // console.log('lastUpdateTime', lastUpdateTime)
        animation.lastUpdateTime = lastUpdateTime;
        state.autoNavAnimation = animation;
      }
    }
  }

  @action
  finishAutoNavigation = (state: MapPageViewState) => {
    if (state.autoNavAnimation) {
      state.viewportCenter = state.autoNavAnimation.endCenter;
      state.viewportHeight = state.autoNavAnimation.endHeight;
      state.autoNavAnimation = null;
    }
    state.mode = MapPageMode.None;
  }
}

export const mapActions = new MapActions();
