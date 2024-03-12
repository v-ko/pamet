import { NO_SCALE_LINE_SPACING } from '../../constants';
import { Point2D } from '../../util/Point2D';
import { RectangleData } from '../../util/Rectangle';
import { Rectangle } from '../../util/Rectangle';


export class Viewport {
  public xReal: number;
  public yReal: number;
  public eye_height: number;
  public geometry: RectangleData;
  private dpr: number = 1; // device pixel ratio

  constructor(realTopLeft: Point2D, eye_height: number, viewport_geometry: RectangleData) {
    this.xReal = realTopLeft.x;
    this.yReal = realTopLeft.y;

    this.eye_height = eye_height;
    this.geometry = viewport_geometry; // In projected space
  }

  get xProjected(): number {
    return this.geometry[1];
  }

  get yProjected(): number {
    return this.geometry[0];
  }

  get realCenter(): Point2D {
    return this.realBounds().center();
  }

  public heightScaleFactor(): number {
    return NO_SCALE_LINE_SPACING / this.eye_height;
  }

  get devicePixelRatio(): number {
    return this.dpr;
  }
  setDevicePixelRatio(dpr: number) {
    this.dpr = dpr;
  }

  moveRealCenterTo(new_center: Point2D) {
    const half_size = this.realBounds().size().divide(2);
    this.xReal = new_center.x - half_size.x;
    this.yReal = new_center.y - half_size.y;
  }

  projectedBounds(): Rectangle {
    return new Rectangle(this.geometry[0], this.geometry[1], this.geometry[2], this.geometry[3]);
  }

  realBounds(): Rectangle {
    return this.unprojectRect(this.projectedBounds());
  }

  public toString(): string {
    const info = `topLeft=${this.xReal},${this.yReal} height=${this.eye_height}`;
    return `<Viewport ${info}>`;
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

  public projectX(xOnPage: number): number {
    // xOnPage -= this.center.x;
    xOnPage -= this.xReal;
    xOnPage *= this.heightScaleFactor();
    // xOnPage = xOnPage + this.geometry[2] / 2;
    return xOnPage;
  }

  public projectY(yOnPage: number): number {
    // yOnPage -= this.center.y;
    yOnPage -= this.yReal;
    yOnPage *= this.heightScaleFactor();
    // yOnPage = yOnPage + this.geometry[3] / 2;
    return yOnPage;
  }

  public unprojectX(xOnScreen: number): number {
    // xOnScreen -= this.geometry[2] / 2;
    xOnScreen /= this.heightScaleFactor();
    // return xOnScreen + this.center.x;
    return xOnScreen + this.xReal;
  }

  public unprojectY(yOnScreen: number): number {
    // yOnScreen -= this.geometry[3] / 2;
    yOnScreen /= this.heightScaleFactor();
    // yOnScreen = yOnScreen + this.center.y;
    yOnScreen = yOnScreen + this.yReal;
    return yOnScreen;
  }
}
