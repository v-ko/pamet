import { Point2D } from "./Point2D"
import { Size } from "./Size";


export type RectangleData = [number, number, number, number];

export class Rectangle {
    constructor(
        public x: number,
        public y: number,
        public w: number,
        public h: number
    ) { }
    static fromPoints(top_left: Point2D, bottom_right: Point2D): Rectangle {
        const size = top_left.subtract(bottom_right)
        const x = Math.min(top_left.x, bottom_right.x)
        const y = Math.min(top_left.y, bottom_right.y)
        const w = Math.abs(size.x)
        const h = Math.abs(size.y)
        return new Rectangle(x, y, w, h)
    }
    data(): RectangleData {
        return [this.x, this.y, this.w, this.h]
    }
    equals(other: Rectangle): boolean {
        return this.data() === other.data()
    }

    get width(): number {
        return this.w
    }
    get height(): number {
        return this.h
    }
    set width(newWidth: number) {
        this.w = newWidth
    }

    size(): Size {
        return new Size(this.w, this.h)
    }
    setSize(new_size: Size) {
        this.w = new_size.width
        this.h = new_size.height
    }
    setWidth(new_width: number) {
        this.w = new_width
    }
    setHeight(new_height: number) {
        this.h = new_height
    }
    setTopLeft(point: Point2D) {
        this.x = point.x
        this.y = point.y
    }
    setX(x: number) {
        this.x = x
    }
    setY(y: number) {
        this.y = y
    }
    moveCenter(point: Point2D) {
        const half_size = this.size().divide(2)
        this.setTopLeft(point.subtract(half_size))
    }
    top(): number {
        return this.y
    }
    left(): number {
        return this.x
    }
    bottom(): number {
        return this.y + this.h
    }
    right(): number {
        return this.x + this.w
    }
    topLeft(): Point2D {
        return new Point2D(this.x, this.y)
    }
    topRight(): Point2D {
        return new Point2D(this.right(), this.top())
    }
    bottomRight(): Point2D {
        return this.topLeft().add(new Point2D(this.w, this.h))
    }
    bottomLeft(): Point2D {
        return new Point2D(this.left(), this.bottom())
    }

    center(): Point2D {
        return this.topLeft().add(this.size().divide(2))
    }
    area(): number {
        return this.w * this.h
    }
    intersection(other: Rectangle): Rectangle | null {
        const a = this
        const b = other
        const x1 = Math.max(Math.min(a.x, a.right()), Math.min(b.x, b.right()))
        const y1 = Math.max(Math.min(a.y, a.bottom()), Math.min(b.y, b.bottom()))
        const x2 = Math.min(Math.max(a.x, a.right()), Math.max(b.x, b.right()))
        const y2 = Math.min(Math.max(a.y, a.bottom()), Math.max(b.y, b.bottom()))

        if (!(x1 < x2 && y1 < y2)) {
            return null
        }

        return new Rectangle(x1, y1, x2 - x1, y2 - y1)
    }

    intersects(other: Rectangle): boolean {
        if (this.intersection(other)) {
            return true
        } else {
            return false
        }
    }
    contains(point: Point2D): boolean {
        return ((this.x <= point.x && point.x <= this.right()) &&
                (this.y <= point.y && point.y <= this.bottom()))
    }
    props(): RectangleData {
        return [this.x, this.y, this.w, this.h]
    }
}
