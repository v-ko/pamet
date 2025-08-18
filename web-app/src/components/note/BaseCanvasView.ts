import { ElementViewState } from "@/components/page/ElementViewState";
import { DirectRenderer } from "@/components/page/DirectRenderer";

export class BaseCanvasView {
    renderer: DirectRenderer;
    elementViewState: ElementViewState;

    constructor(renderer: DirectRenderer, elementViewState: ElementViewState) {
        this.renderer = renderer;
        this.elementViewState = elementViewState;
    }
}
