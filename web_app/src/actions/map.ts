import { SelectionDict } from "../util";
import { action, makeObservable } from "mobx";
import { MapPageViewState } from "../components/MapPage";
import { Point2D } from "../util/Point2D";


class MapActions {
  constructor() {
    makeObservable(this);
  }

  @action
  updateViewport (
    state: MapPageViewState,
    viewportCenter: Point2D,
    viewportHeight: number) {
  state.viewportCenter = viewportCenter
  state.viewportHeight = viewportHeight
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
}

export const mapActions = new MapActions();
