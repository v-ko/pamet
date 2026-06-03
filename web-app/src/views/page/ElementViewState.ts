import { Change } from "sivkit/model/Change";
import { PametElement, PametElementData } from "@/model/Element";
import { PageViewState } from "@/views/page/PageViewState";
import { dumpToDict, SerializedEntityData } from "sivkit/model/Entity";

export abstract class ElementViewState {
    _elementData: SerializedEntityData;
    pageViewState: PageViewState;
    constructor(element: PametElement<PametElementData>, pageViewState: PageViewState) {
        this._elementData = dumpToDict(element);
        this.pageViewState = pageViewState;
    }

    abstract element(): PametElement<PametElementData>;

    abstract updateFromChange(change: Change): void;
}
