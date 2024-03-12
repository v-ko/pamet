import { NoteCanvasView } from "./components/note/NoteCanvasView";
import { PageChild } from "./model/PageChild";


export type ElementView<T extends typeof NoteCanvasView> = T | React.FC<any>;

let _elementTypeToViewMap: Map<typeof PageChild<any>, ElementView<any>> = new Map();

export function registerElementView<T extends typeof PageChild<any>>(stateType: T, elementViewType: ElementView<any>) {
    _elementTypeToViewMap.set(stateType, elementViewType);
}

export function getElementView<T extends typeof PageChild<any>>(stateType: T): ElementView<any> {
    if (!_elementTypeToViewMap.has(stateType)) {
        throw new Error(
            `No view registered for element type ${stateType.name}. Do a dummy import in the index.tsx to trigger the registration if you haven't.`);
    }
    return _elementTypeToViewMap.get(stateType);
}
