import { computed, makeAutoObservable } from 'mobx';
import { DEFAULT_EYE_HEIGHT } from '../../constants';
import { Point2D } from '../../util/Point2D';
import { MapPageData } from '../../model/MapPage';
import { Viewport } from '../Viewport';


export interface ViewportAutoNavAnimation {
  startCenter: Point2D;
  endCenter: Point2D;
  startHeight: number;
  endHeight: number;
  startTime: number;
  duration: number;
  lastUpdateTime?: number;
  timingFunctionName: string;
}


// Mode enumeration
export enum MapPageMode {
  None,
  DragNavigation,
  DragSelection,
  NoteResize,
  ChildMove,
  CreateArrow,
  ArrowEdgeDrag,
  AutoNavigation
}


export class MapPageViewState {
  page: MapPageData;
  // note_view_states: { [id: string]: NoteViewState } = {};
  // arrow_view_states: { [id: string]: ArrowViewState } = {};
  mode: MapPageMode = MapPageMode.None;

  viewportCenter: Point2D = new Point2D(0, 0);
  viewportHeight: number = DEFAULT_EYE_HEIGHT;
  geometry: [number, number, number, number] = [0, 0, 0, 0];

  // Helper props
  viewportCenterOnModeStart: Point2D | null = null;

  // Drag navigation
  dragNavigationStartPosition: Point2D | null = null;

  //
  selection: Array<string> = [];

  autoNavAnimation: ViewportAutoNavAnimation | null = null;

  constructor(page: MapPageData) {
    this.page = page;
    makeAutoObservable(this);
  }

  clear_mode() {
    this.mode = MapPageMode.None;

    this.dragNavigationStartPosition = null;
    this.viewportCenterOnModeStart = null;
  }

  set_mode(mode: MapPageMode) {
    if (this.mode !== MapPageMode.None) {
      this.clear_mode();
    }
    this.mode = mode;
  }

  @computed
  get viewport() {  // Todo: make this a computed property?
    return new Viewport(this.viewportCenter, this.viewportHeight, this.geometry);
  }
}
