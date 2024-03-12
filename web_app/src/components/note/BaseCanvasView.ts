import { PageChildViewState } from "../canvas/PageChildViewState";
import { CanvasPageRenderer } from "../canvas/canvasPageRenderer";

export class BaseCanvasView {
    renderer: CanvasPageRenderer;
    elementViewState: PageChildViewState;

    constructor(renderer: CanvasPageRenderer, elementViewState: PageChildViewState) {
        this.renderer = renderer;
        this.elementViewState = elementViewState;
    }
}
