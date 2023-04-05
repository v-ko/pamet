import { SelectionDict } from '../types/util';

//translate(${props => props.center[0]}, ${props => props.center[1]})
export class MapController {
  selection: Array<string>;
  setSelection: (selection: Array<string>) => void;
  constructor(selection: Array<string>, setSelection: (selection: Array<string>) => void) {
    this.selection = selection;
    this.setSelection = setSelection;
  }
  updateSelection = (selectionDict: SelectionDict) => {
    // Add all keys that are true to the selection
    let newSelection: Array<string> = this.selection;
    for (let key in selectionDict) {
      if (selectionDict[key] && !this.selection.includes(key)) {
        newSelection.push(key);
      }
    }
    // remove all keys that are false from the selection
    newSelection = newSelection.filter((key) => selectionDict[key] !== false);
    this.selection = newSelection;
    this.setSelection(newSelection);
  };
  clearSelection = () => {
    let selectionDict: SelectionDict = {};
    for (let noteId of this.selection) {
      selectionDict[noteId] = false;
    }
    this.updateSelection(selectionDict);
  };
}
