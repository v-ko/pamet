import { Change } from "fusion/Change";
import { PametElement, PametElementData } from "../../model/Element";

export abstract class ElementViewState {
    abstract element(): PametElement<PametElementData>;
    abstract updateFromChange(change: Change): void;
}
