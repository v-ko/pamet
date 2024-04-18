import { PametElement, PametElementData } from "../../model/Element";

export abstract class ElementViewState {
    abstract element(): PametElement<PametElementData>;
}
