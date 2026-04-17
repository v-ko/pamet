import { NO_SCALE_LINE_SPACING } from "@/core/constants";
import { Point2D } from 'fusion/primitives/Point2D';
import { RectangleData } from 'fusion/primitives/Rectangle';
import { Rectangle } from 'fusion/primitives/Rectangle';


function unprojectX(xOnScreen: number, viewportLeftReal: number, heightScaleFactor: number): number {
  xOnScreen /= heightScaleFactor;
  return xOnScreen + viewportLeftReal;
}
function unprojectY(yOnScreen: number, viewportTopReal: number, heightScaleFactor: number): number {
  yOnScreen /= heightScaleFactor;
  return yOnScreen + viewportTopReal;
}

export interface ViewportData {
  eyeHeight: number;
  realGeometry: RectangleData;
}

export class Viewport {
  public eyeHeight: number;
  private _realGeometry: RectangleData;

  private dpr: number = 1; // device pixel ratio

  constructor(realGeometry: RectangleData, eye_height: number) {
    this._realGeometry = realGeometry;
    this.eyeHeight = eye_height;
  }

  static fromProjectedGeometry(projected: RectangleData, eye_height: number): Viewport {
    const heightScaleFactor = NO_SCALE_LINE_SPACING / eye_height;
    let realGeometry: RectangleData = [
      unprojectX(projected[0], 0, heightScaleFactor),
      unprojectY(projected[1], 0, heightScaleFactor),
      projected[2] / heightScaleFactor,
      projected[3] / heightScaleFactor
    ]
    return new Viewport(realGeometry, eye_height);
  }

  // Getters
  get xReal(): number {
    return this._realGeometry[0];
  }
  get yReal(): number {
    return this._realGeometry[1];
  }

  get realBounds(): Rectangle {
    return new Rectangle(this._realGeometry)
  }

  realCenter(): Point2D {
    return this.realBounds.center();
  }

  public heightScaleFactor(): number {
    return NO_SCALE_LINE_SPACING / this.eyeHeight;
  }

  // Setters

  moveRealCenterTo(new_center: Point2D) {
    const half_size = this.realBounds.size();
    half_size.divide_inplace(2);
    this._realGeometry[0] = new_center.x - half_size.x;
    this._realGeometry[1] = new_center.y - half_size.y;
  }

  // Device pixel ratio related
  get devicePixelRatio(): number {
    return this.dpr;
  }
  setDevicePixelRatio(dpr: number) {
    this.dpr = dpr;
  }

  // Helpers
  public toString(): string {
    const info = `topLeft=${this.xReal},${this.yReal} height=${this.eyeHeight}`;
    return `<Viewport ${info}>`;
  }

  // Transformation functions
  public projectX(xOnPage: number): number {
    xOnPage -= this.xReal;
    xOnPage *= this.heightScaleFactor();
    return xOnPage;
  }

  public projectY(yOnPage: number): number {
    yOnPage -= this.yReal;
    yOnPage *= this.heightScaleFactor();
    return yOnPage;
  }

  public unprojectX(xOnScreen: number): number {
    xOnScreen /= this.heightScaleFactor();
    return xOnScreen + this.xReal;
  }

  public unprojectY(yOnScreen: number): number {
    yOnScreen /= this.heightScaleFactor();
    yOnScreen = yOnScreen + this.yReal;
    return yOnScreen;

  }

  public projectPoint(point: Point2D): Point2D {  // TODO: optimize this
    const x = this.projectX(point.x);
    const y = this.projectY(point.y);
    return new Point2D([x, y]);
  }

  public unprojectPoint(point: Point2D): Point2D {
    const x = this.unprojectX(point.x);
    const y = this.unprojectY(point.y);
    return new Point2D([x, y]);
  }

  public projectRect(rect: Rectangle): Rectangle {
    const top_left = this.projectPoint(rect.topLeft());
    const bottom_right = this.projectPoint(rect.bottomRight());
    return Rectangle.fromPoints(top_left, bottom_right);
  }

  public unprojectRect(rect: Rectangle): Rectangle {
    const top_left = this.unprojectPoint(rect.topLeft());
    const bottom_right = this.unprojectPoint(rect.bottomRight());
    return Rectangle.fromPoints(top_left, bottom_right);
  }
}
