import { ElementViewState } from "../page/ElementViewState";
import { CanvasPageRenderer } from "../page/DirectRenderer";

export class BaseCanvasView {
    renderer: CanvasPageRenderer;
    elementViewState: ElementViewState;

    constructor(renderer: CanvasPageRenderer, elementViewState: ElementViewState) {
        this.renderer = renderer;
        this.elementViewState = elementViewState;
    }
}
