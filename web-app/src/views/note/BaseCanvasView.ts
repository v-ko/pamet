import { ElementViewState } from "@/views/page/ElementViewState";
import { DirectRenderer } from "@/views/page/DirectRenderer";

export class BaseCanvasView {
    renderer: DirectRenderer;
    elementViewState: ElementViewState;

    constructor(renderer: DirectRenderer, elementViewState: ElementViewState) {
        this.renderer = renderer;
        this.elementViewState = elementViewState;
    }
}
