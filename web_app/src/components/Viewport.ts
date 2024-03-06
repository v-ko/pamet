import { NO_SCALE_LINE_SPACING } from '../constants';
import { Point2D } from '../util/Point2D';
import { RectangleData } from '../util/Rectangle';
import { Rectangle } from '../util/Rectangle';


export class Viewport {
  public center: Point2D;
  public eye_height: number;
  public geometry: RectangleData;

  constructor(view_center: Point2D, eye_height: number, viewport_geometry: RectangleData) {
    this.center = view_center;
    this.eye_height = eye_height;
    this.geometry = viewport_geometry;
  }

  get pixelSpaceRect(): Rectangle {
    return new Rectangle(this.geometry[0], this.geometry[1], this.geometry[2], this.geometry[3]);
  }

  public toString(): string {
    const info = `center=${this.center.toString()} height=${this.eye_height}`;
    return `<Viewport ${info}>`;
  }

  public heightScaleFactor(): number {
    return NO_SCALE_LINE_SPACING / this.eye_height;
  }

  public projectRect(rect: Rectangle): Rectangle {
    const top_left = this.projectPoint(rect.topLeft());
    const bottom_right = this.projectPoint(rect.bottomRight());
    return Rectangle.fromPoints(top_left, bottom_right);
  }

  public projectPoint(point: Point2D): Point2D {
    const x = this.projectX(point.x);
    const y = this.projectY(point.y);
    return new Point2D(x, y);
  }

  public projectX(xOnPage: number): number {
    xOnPage -= this.center.x;
    xOnPage *= this.heightScaleFactor();
    return xOnPage + this.geometry[2] / 2;
  }

  public projectY(yOnPage: number): number {
    yOnPage -= this.center.y;
    yOnPage *= this.heightScaleFactor();
    return yOnPage + this.geometry[3] / 2;
  }

  public unprojectPoint(point: Point2D): Point2D {
    const x = this.unprojectX(point.x);
    const y = this.unprojectY(point.y);
    return new Point2D(x, y);
  }

  public unprojectRect(rect: Rectangle): Rectangle {
    const top_left = this.unprojectPoint(rect.topLeft());
    const bottom_right = this.unprojectPoint(rect.bottomRight());
    return Rectangle.fromPoints(top_left, bottom_right);
  }

  public unprojectX(xOnScreen: number): number {
    xOnScreen -= this.geometry[2] / 2;
    xOnScreen /= this.heightScaleFactor();
    return xOnScreen + this.center.x;
  }

  public unprojectY(yOnScreen: number): number {
    yOnScreen -= this.geometry[3] / 2;
    yOnScreen /= this.heightScaleFactor();
    return yOnScreen + this.center.y;
  }
}
