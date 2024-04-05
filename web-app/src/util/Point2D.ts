// import { Point2D } from '../types/util';
export type PointData = [number, number];

export class Vector2D {
  constructor(public x: number = 0, public y: number = 0) { }

  equals(other: Vector2D): boolean {
    return this.x === other.x && this.y === other.y;
  }

  add(other: Vector2D): this {
    return new (this.constructor as any)(this.x + other.x, this.y + other.y);
  }

  subtract(other: Vector2D): this {
    return new (this.constructor as any)(this.x - other.x, this.y - other.y);
  }

  divide(k: number): this {
    return new (this.constructor as any)(this.x / k, this.y / k);
  }

  round(): this {
    return new (this.constructor as any)(Math.round(this.x), Math.round(this.y));
  }

  multiply(k: number): this {
    return new (this.constructor as any)(this.x * k, this.y * k);
  }
}

export class Point2D  extends Vector2D {

  static fromData(obj: PointData): Point2D {
    return new Point2D(obj[0], obj[1]);
  }

  data(): PointData {
    return [this.x, this.y];
  }

  copy(): Point2D {
    return new Point2D(this.x, this.y);
  }

  toString(): string {
    return `<Point x=${this.x} y=${this.y}>`;
  }

  distanceTo(point: Point2D): number {
    const distance = Math.sqrt(
      Math.pow(this.x - point.x, 2) + Math.pow(this.y - point.y, 2)
    );
    return distance;
  }

  rotated(radians: number, origin: Point2D): Point2D {
    const adjustedX = this.x - origin.x;
    const adjustedY = this.y - origin.y;
    const cosRad = Math.cos(radians);
    const sinRad = Math.sin(radians);
    const qx = origin.x + cosRad * adjustedX + sinRad * adjustedY;
    const qy = origin.y - sinRad * adjustedX + cosRad * adjustedY;
    return new Point2D(qx, qy);
  }
}
