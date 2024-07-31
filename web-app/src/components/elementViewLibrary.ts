import { NoteCanvasView } from "./note/NoteCanvasView";
import { PametElement } from "../model/Element";


export type ElementView<T extends typeof NoteCanvasView> = T | React.FC<any>;

let _elementTypeToViewMap: Map<typeof PametElement<any>, ElementView<any>> = new Map();

export function registerElementView<T extends typeof PametElement<any>>(stateType: T, elementViewType: ElementView<any>) {
    _elementTypeToViewMap.set(stateType, elementViewType);
}

export function getElementView<T extends typeof PametElement<any>>(stateType: T): ElementView<any> {
    if (!_elementTypeToViewMap.has(stateType)) {
        throw new Error(
            `No view registered for element type ${stateType.name}. Do a dummy import in the index.tsx to trigger the registration if you haven't.`);
    }
    return _elementTypeToViewMap.get(stateType);
}
