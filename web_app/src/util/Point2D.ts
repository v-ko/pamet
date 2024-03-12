// import { Point2D } from '../types/util';
export type PointData = [number, number];

export class Point2D {
  constructor(public x: number = 0, public y: number = 0) { }

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

  equals(other: Point2D): boolean {
    return this.x === other.x && this.y === other.y;
  }

  add(other: Point2D): Point2D {
    return new Point2D(this.x + other.x, this.y + other.y);
  }

  subtract(other: Point2D): Point2D {
    return new Point2D(this.x - other.x, this.y - other.y);
  }

  divide(k: number): Point2D {
    return new Point2D(this.x / k, this.y / k);
  }

  round(): Point2D {
    return new Point2D(Math.round(this.x), Math.round(this.y));
  }

  multiply(k: number): Point2D {
    return new Point2D(this.x * k, this.y * k);
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
