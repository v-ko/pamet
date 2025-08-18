import { Change } from "fusion/model/Change";
import { PametElement, PametElementData } from "@/model/Element";
import { PageViewState } from "@/components/page/PageViewState";
import { dumpToDict, SerializedEntityData } from "fusion/model/Entity";

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
