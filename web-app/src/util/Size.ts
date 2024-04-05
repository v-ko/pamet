import { Vector2D } from "./Point2D";

export type SizeData = [number, number];

export class Size extends Vector2D {

    constructor(width: number, height: number) { // Kept for annotation
        super(width, height);
    }

    get width(): number {
        return this.x;
    }

    get height(): number {
        return this.y;
    }

    set width(width: number) {
        this.x = width;
    }

    set height(height: number) {
        this.y = height;
    }

    data(): SizeData {
        return [this.x, this.y];
    }
}
