import { ElementViewState } from "@/components/page/ElementViewState";
import { CanvasPageRenderer } from "@/components/page/DirectRenderer";

export class BaseCanvasView {
    renderer: CanvasPageRenderer;
    elementViewState: ElementViewState;

    constructor(renderer: CanvasPageRenderer, elementViewState: ElementViewState) {
        this.renderer = renderer;
        this.elementViewState = elementViewState;
    }
}
